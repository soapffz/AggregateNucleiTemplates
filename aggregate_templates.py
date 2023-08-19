"""
文件名: aggregate_templates.py
作者: soapffz
创建时间: 2023年7月19日
最后修改时间: 2023年8月20日

脚本描述:
这个脚本是用于管理和更新GitHub上的仓库模板的。它可以克隆仓库，更新仓库，检查仓库状态，移除重复和危害较低的模板，并将所有模板移动到"ALL"文件夹。

主要功能:
1. 克隆或更新指定的GitHub仓库。如果仓库已存在，将跳过克隆；如果仓库不存在，将跳过更新。
2. 检查GitHub仓库的状态，包括仓库是否被归档。如果仓库已被归档，脚本仍将尝试克隆或更新。
3. 移除重复的模板，通过计算文件的MD5哈希值来判断是否重复。
4. 移除等级为info、low的模板。
5. 将所有的模板复制到"ALL"文件夹。脚本运行时会删除"ALL"文件夹并重新创建。

注意事项:
1. 需要在运行脚本前配置GitHub token，你可以在这里生成一个新的token: https://github.com/settings/tokens
2. 如果无法访问GitHub API，建议开启代理后再次运行当前脚本。
3. 脚本使用多线程进行仓库的克隆和更新，以提高效率。
4. 脚本使用了LRU缓存来优化加载yaml文件的性能。
5. 脚本提供了两种运行模式：一次性输出所有唯一脚本到ALL文件夹，或定时任务中定期执行，只对所有仓库进行git pull更新。
"""

import os
import hashlib
from github import Github
from git import Repo
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import json
import shutil
import argparse
from git import Git, GitCommandError
from functools import lru_cache
import urllib.parse
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 读取配置文件
with open("config.json", "r") as file:
    config = json.load(file)
g = Github(config["token"])  # Github token

repositories = config["repositories"]  # 仓库列表
blacklist = config["blacklist"]  # 黑名单列表


def check_github_token():
    """检查GitHub token的有效性"""
    try:
        g = Github(config["token"])  # Github token
    except AssertionError:
        logging.error(
            "GitHub token未配置，你可以在这里生成一个新的token: https://github.com/settings/tokens"
        )
        exit(1)


def generate_local_repo_name(repo_url):
    """生成本地仓库名称"""
    parsed_url = urllib.parse.urlparse(repo_url)
    repo_name = parsed_url.path.lstrip("/")
    # 移除特殊字符
    repo_name = re.sub(r"\W+", "_", repo_name)
    return repo_name


def handle_repository(repo_url, operation):
    """处理一个仓库，包括克隆和更新"""
    repo_name = generate_local_repo_name(repo_url)
    if operation == "clone" and os.path.exists(repo_name):
        logging.warning(f"仓库 {repo_name} 已存在，跳过克隆")
        return False
    if operation == "update" and not os.path.exists(repo_name):
        logging.warning(f"仓库 {repo_name} 不存在，跳过更新")
        return False
    try:
        if operation == "clone":
            Git().clone(repo_url, repo_name)
        else:
            repo = Repo(repo_name)
            repo.git.pull()
        return True
    except Exception as e:
        logging.error(f"处理 {repo_url} 失败，错误信息: {str(e)}")
        return False


def remove_duplicated_templates(hashes):
    """移除重复的模板"""
    count = 0
    for file_path in Path(".").rglob("*.y*ml"):
        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        if file_hash in hashes:
            file_path.unlink()
            count += 1
        else:
            hashes.add(file_hash)
    logging.info(f"删除了 {count} 个重复的模板")


@lru_cache(maxsize=None)
def load_yaml(file_path):
    """加载yaml文件"""
    return yaml.safe_load(file_path.read_text())


def remove_info_severity_templates():
    """移除等级为info、low的模板"""
    count = 0
    for file_path in Path(".").rglob("nuclei_/**/*.y*ml"):
        content = load_yaml(file_path)
        # 如果严重性为info、low，删除它
        info_content = content.get("info")
        if info_content is not None:
            severity = info_content.get("severity", "")
            if "info" in severity or "low" in severity:
                file_path.unlink()
                count += 1
    logging.info(f"删除了 {count} 个威胁较低的模板")


def main(repositories, all=False, update=False):
    """主函数"""
    if not (all or update):
        parser.print_help()
        exit(0)

    check_github_token()

    success_count = 0
    with ThreadPoolExecutor() as executor:
        if all:
            futures = [
                executor.submit(handle_repository, repo_url, "clone")
                for repo_url in repositories
                if repo_url not in blacklist
            ]
        else:
            futures = [
                executor.submit(handle_repository, repo_url, "update")
                for repo_url in repositories
                if repo_url not in blacklist
            ]
        for future in as_completed(futures):
            if future.result():
                success_count += 1

    logging.info(f"成功处理了 {success_count} 个仓库")

    hashes = set()
    remove_duplicated_templates(hashes)
    remove_info_severity_templates()

    if Path("ALL").exists():
        shutil.rmtree("ALL")
    Path("ALL").mkdir()
    for file_path in Path(".").rglob("*.y*ml"):
        if file_path.parent.name != "ALL":
            destination = Path("ALL") / file_path.name
            if not destination.exists():
                shutil.copy2(file_path, destination)
                if update:
                    logging.info(f"新增模板: {file_path.name}")

    total_templates = sum(1 for _ in Path("ALL").iterdir())
    logging.info(f"唯一模板总数: {total_templates}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-all", action="store_true", help="一次性输出所有唯一脚本到ALL文件夹")
    parser.add_argument(
        "-update", action="store_true", help="定时任务中定期执行，只对所有仓库进行git pull更新"
    )
    args = parser.parse_args()
    main(repositories, args.all, args.update)
