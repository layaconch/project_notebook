# DevOps Operations Platform | DevOps 运维平台

## Overview | 概览
A lightweight DevOps/ops addon for Odoo 18 with notebooks, data sources, requirements, and issue tracking.
面向 Odoo 18 的轻量 DevOps/运维模块，包含笔记本、数据源、需求和问题跟踪。

## Features | 功能
- Notebook: Markdown/Python/SQL cells, rendered output, stats; supports PostgreSQL/Oracle/MSSQL/CSV data sources; run-all and per-cell execution.
- Data Sources: Manage DB/file connections with connectivity test; PostgreSQL search_path/schema, Oracle instantclient helper.
- Requirements & Issues: Simple tracking with owners/status.
- Notebook Categories & Permissions: Categories with public flag or allowed user groups; list/form/kanban/graph/pivot; DevOps user/manager groups.
- UI: Backend SCSS tuned for notebook layout; inputs highlighted; developer mode kept on in docker config.

- 笔记本：支持 Markdown/Python/SQL 单元与渲染输出，统计执行情况；可配置 PostgreSQL/Oracle/MSSQL/CSV 数据源；支持单元/全部运行。
- 数据源：集中维护数据库/文件连接，带连通性测试；PostgreSQL 支持 search_path/schema；Oracle 自动加载 instantclient。
- 需求/问题：轻量化记录负责人与状态。
- 笔记本分类与权限：分类可公共或按用户组授权；提供列表/表单/看板/图表/数据透视视图；内置 DevOps 用户与管理员组。
- 界面：优化笔记本布局和输入高亮；容器配置保持开发者模式。

## Installation | 安装
1) Clone into your addons path (default `/mnt/extra-addons` in docker-compose).  
2) Update app list and install “DevOps Operations Platform”.
3) For docker compose in this repo:
   ```bash
   cd /home/cheap/odoo18_docker
   docker compose up -d
   ./upgrade_devops.sh <db_name>   # e.g. dev00
   ```

1) 将仓库克隆到 addons 路径（compose 默认 `/mnt/extra-addons`）。  
2) 更新应用列表，安装 “DevOps Operations Platform”。  
3) 使用本仓库 docker-compose：
   ```bash
   cd /home/cheap/odoo18_docker
   docker compose up -d
   ./upgrade_devops.sh <数据库名>   # 如 dev00
   ```

## Usage Highlights | 使用要点
- Set default data source in Settings → DevOps block.
- Maintain data sources under DevOps → Settings (only admins).
- Create categories and assign allowed user groups; public categories are visible/runnable to all.
- Maintain DevOps groups under DevOps → Settings → DevOps Groups.
- Run notebooks via Run All or per cell; SQL outputs render styled tables.

- 在“设置 → DevOps”里配置默认数据源。  
- 数据源维护位于 DevOps → Settings（仅管理员）。  
- 创建分类并设定允许的用户组；公共分类对所有人可见/可执行。  
- DevOps 用户组维护：DevOps → Settings → DevOps Groups。  
- 笔记本支持“全部运行”或单元运行，SQL 输出带样式化表格。

## Development | 开发
- Upgrade after code changes: `cd /home/cheap/odoo18_docker && ./upgrade_devops.sh <db_name>`.
- Pinned images in `odoo18_docker/docker-compose.yml`: `odoo:18.0-20251106`, `postgres:16.4`.
- Use branch `main`, tag releases (e.g., `0.1`) and push to origin.

- 代码变更后请执行升级同步：`cd /home/cheap/odoo18_docker && ./upgrade_devops.sh <数据库名>`。  
- compose 已锁定镜像：`odoo:18.0-20251106`、`postgres:16.4`。  
- 使用 main 分支，打标签发布（如 `0.1`）并推送即可。
