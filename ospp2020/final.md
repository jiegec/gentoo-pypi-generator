# 结项报告

## 项目信息

- 项目名称：Gentoo PyPI ebuild 生成器
- 方案描述：
  1. 实现 PyPI 所有 Python 包的元数据的抓取和解析
  2. 基于 python eclass 实现一个用于 pypi 的 eclass
  3. 按照 PyPI 上的元数据，指定一个包，生成它和它的所有依赖的对应的 ebuild
  4. 通过 CI 进行测试，测试安装指定的一些 package 并进行测试
- 时间规划：
  1. 7.1-7.15 两星期：了解 gs-pypi 工作原理，尝试手动编写一个类似的 ebuild 并进行测试
  2. 7.16-7.31 两星期：使用 Python 编写简单的 ebuild 生成器，并把通用的部分写到单独的 eclass 中
  3. 8.1-8.15 两星期：优化 ebuild 生成器，支持更复杂的依赖关系，并可以生成包和包的依赖的所有 ebuild
  4. 8.16-8.31 两星期：支持多 Python 版本共存，实现 CI 自动测试
  5. 9.1-9.15 两星期：编写文档，设计非标准 pypi 包的 ebuild 方案
  6. 9.16-9.30 两星期：和认识的 Gentoo 用户进行实际测试，按照反馈进行改善

## 项目进度

- 已完成工作：
  1. 配置了在 Docker 中的 gentoo 环境，方便开发和自动测试，容器内包含了常用的工具，加快了编译构建的速度
  2. 编写了 python 脚本，可以从 pypi 上抓取元数据并生成基于 distutils-r1.eclass 的 ebuild 文件，并自动翻译库的依赖信息，可以翻译比较复杂的依赖表达式
  3. 实现了对已有 ebuild 的包的扫描，可以自动跳过已经生成或者已经在 gentoo 仓库中的 ebuild
  4. 基于 3，自动递归地生成新的 ebuild，并且生成对应的 Manifest 文件
  5. 配置 CI，自动按照列表，生成指定的测试包的 ebuild
  6. 发布了 gentoo-sci-pypi overlay，含有本生成器生成的若干已经测试过的 ebuild 文件
  7. 采用 pytest 作为默认的测试框架，在 emerge 构建的时候启用 test FEATURE 即可进行测试
  8. 支持了常见的一些 pypi 上的包，比如 jupyter、scikit-learn 和 xgboost 等等