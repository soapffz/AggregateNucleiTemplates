# 项目介绍

这是一个 Python 脚本，用于从 GitHub 上的多个仓库中获取 Nuclei 模板。它可以检查 GitHub 令牌的有效性，检查 GitHub API 的可用性，克隆或更新仓库，移除重复和过时的模板，并将所有模板移动到"ALL"文件夹。

## 使用方法

1. 配置你的 GitHub 令牌和要获取模板的仓库列表。这些信息需要在`config.json`文件中配置。

```bash
{
    "token": "your_github_token",
    "repositories": [
        "https://github.com/projectdiscovery/nuclei-templates",
        "https://github.com/1in9e/my-nuclei-templates",
        ...
    ]
}
```

2. 运行`aggregate_templates.py`脚本来获取模板。你可以使用`-all`参数一次性输出所有唯一脚本到 ALL 文件夹，或者使用`-update`参数定时任务中定期执行，只对所有仓库进行 git pull 更新。

```bash
python3 aggregate_templates.py -all
```

![-all参数运行示例](https://img.soapffz.com/soapsgithubimgs/AggregateNucleiTemplates运行示例1.png)

或者

```bash
python3 aggregate_templates.py -update
```

## 与 reNgine 联动

默认 reNgine 只使用 ssrf_nagli.yaml 一个文件，连官方自带的其他的脚本都不使用，以下为 reNgine v1.3.6 版本在 debian 默认安装后，进入 docker 容器使用本项目批量添加模版的操作步骤

```bash
# 进入容器
docker exec -it rengine-celery-1 bash

# 下载当前项目，配置github token
apt-get install vim -y && cd  ~/nuclei-templates/ && git clone https://github.com/soapffz/AggregateNucleiTemplates && cd AggregateNucleiTemplates/ && pip3 install -r requirements.txt && cp config.json.example config.json && vim config.json

# 执行下载脚本
python3 aggregate_templates.py -all

# 将脚本复制到当前目录（先别急着退出shell）
cp ALL/*.yaml ~/nuclei-templates/
```

此时在 reNgine 的 Tool Settings 中即可看到 nuclei 处已经爆炸

除此之外还需在 reNgine 的 Scan Engine 把所有的 yaml 文件名添加一下

生成文件名

```bash
find . -maxdepth 1 -name "*.yaml" -exec basename {} .yaml \; | tr '\n' ',' | sed 's/,$/\n/' | sed 's/,/, /g' > names.txt
```

复制到宿主机，在宿主机运行

```bash
docker cp rengine-celery-1:/root/nuclei-templates/names.txt .
```

下载到本地，打开 reNgine -> Scan Engine -> 编辑你常用的扫描模式例如 Full Scan -> 最后两行默认

```bash
  # custom_templates: []
  severity: [ critical, high, medium, low, info, unknown ]
```

把注释去掉，把 names.txt 生成的内容粘贴进去[]，括号前后各留一个空格

severity 删除, low, info

![reNgine-ScanEngine修改nuclei配置](https://img.soapffz.com/soapsgithubimgs/reNgine-ScanEngine修改nuclei配置.png)

## 注意事项

1. 请确保你的 GitHub 令牌具有足够的权限来访问你想要获取模板的仓库。
2. 如果你的网络环境无法直接访问 GitHub，你可能需要配置代理。
3. 请确保你的 Python 环境已经安装了所有必要的依赖库，如 requests、github、git 等。

## 更新日志

- 2023 年 8 月 19 日：完善项目，上传到 github，项目状态为公开，-all 全量下载并去重没啥问题了，-update 更新脚本还没有详细测试
- 2023 年 7 月 19 日：初始化项目
