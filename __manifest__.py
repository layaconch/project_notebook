{
    "name": "DevOps Operations Platform",
    "version": "1.0.0",
    "summary": "DevOps platform with notebooks, requirements, and issue tracking",
    "description": """Interactive notebooks with multi-database data sources plus lightweight requirement and issue management.""",
    "category": "DevOps",
    "author": "In-house",
    "license": "LGPL-3",
    "website": "https://example.com",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/devops_notebook_views.xml",
        "views/devops_data_source_views.xml",
        "views/devops_requirement_views.xml",
        "views/devops_issue_views.xml",
        "views/res_config_settings_views.xml",
        "views/devops_menu.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "devops/static/src/scss/notebook.scss",
        ],
    },
    "application": True,
    "auto_install": False,
}
