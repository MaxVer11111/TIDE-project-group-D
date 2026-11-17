# TIDE project — Group D

D组第1–4周研究、内容验证、mock行为测试及ITB初步实验交付。

## 阅读入口

- [交付物目录](D组交付物/README.md)
- [研究与实验报告](D组交付物/01_第1至4周研究与实验报告.md)
- [样例数据与跨组实际输入对照](D组交付物/05_样例数据与跨组实际输入对照.md)
- [测试矩阵与接口对接](D组交付物/02_测试矩阵与接口对接.md)
- [原生ITB结果](D组交付物/ITB/运行状态.md)

下载仓库后，可用浏览器打开 `D组交付物/交付物总览.html`。GitHub文件页面展示HTML源码，不自动运行该总览。

## 结果与边界

内容检查20/20、进程内mock断言26/26、ITB 1.30.3原生Session 8/8，准确原因复核8/8。原始失败、导入错误和修复后结果均保留。

所有业务输入来自教学样例或明确模拟状态；真实的是Validator与ITB执行。尚未完成A/B实际身份、审批、EDC交换或Benchmark集成；跨组缺口已逐项标注。P4 fixture分数不是计算结果。

## 本地复现

Python 3.13；PowerShell示例：

```powershell
# 原生成器重建P1/P2教学合成数据；不是企业生产数据。
python TIDE_Minimal_Research_Scenario/scripts/generate_data.py
cd D组交付物
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install --index-url https://pypi.org/simple -r requirements.lock.txt
./run-all.ps1
```

生成器固定种子为1101/2202。运行后应按原清单/hash验证；若环境或生成器变更导致不一致，应检查原因，不直接改写既有成功证据。P2逐条CSV未上传，生成后仅保留在本地提供方区域；由`.gitignore`排除。

ITB：`docker compose -f ITB/compose.yaml up -d --build`，本机访问 http://localhost:19000 。首次初始化和原生复跑详见[复现指南](D组交付物/03_复现与演示指南.md)。Master API key在本地交互输入或进程环境中配置，不放入Git仓库。

## 内容来源与许可

场景与合成数据使用说明见 [TERMS.md](TIDE_Minimal_Research_Scenario/data/TERMS.md)。保留了pySHACL调用链研究所用源码及对应许可，位于 `D组交付物/研究源码/`。第三方工具遵循各自许可证；本仓库未替第三方代码授予额外许可。

虚拟环境、缓存、认证信息与P2逐条CSV不属于本次上传内容。文件字节hash索引位于 `D组交付物/交付文件hash.json`；`.gitattributes`保留字节内容，避免换行转换破坏证据hash。
