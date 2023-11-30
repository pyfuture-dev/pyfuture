# PyFuture
一个用于提前使用 Python 新特性的工具

## 开发手册
确保满足如下环境要求后，执行 `pdm install` 安装依赖。
- Python 3.12+
- PDM

在打包的时候要添加 `no-isolation` 参数且当前环境已经安装好 `pdm install` 了，
因为打包时会运行 `build_hook`，依赖于 `pyfuture` 本身。
```bash
pdm build --no-isolation
```
