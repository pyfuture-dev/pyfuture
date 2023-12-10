# PyFuture
一个用于提前使用 Python 新特性的工具

## 代码转写层级
rule: 转写规则，比如替换 `type` 关键字。
rule set: 转写规则集，比如 `PEP695` 相关的转写规则，包含若干转写规则。

version related rule sets: 版本相关转写规则集，比如 `3.12` 版本相关的转写规则集，包括 `PEP695` 和 `PEP701` 两个，每个版本可能包含可选规则集。

## 开发手册
确保满足如下环境要求后，执行 `pdm install` 安装依赖。
- Python 3.12+
- PDM

在打包的时候要添加 `no-isolation` 参数且当前环境已经安装好 `pdm install` 了，
因为打包时会运行 `build_hook`，依赖于 `pyfuture` 本身。
```bash
pdm build --no-isolation
```
