from odoo.tests import TransactionCase
from unittest.mock import patch
import pandas as pd

class TestNotebookSQLPandas(TransactionCase):
    def setUp(self):
        super().setUp()
        self.notebook = self.env["devops.notebook"].create({"name": "Test Notebook"})
        self.sql_cell = self.env["devops.notebook.cell"].create({
            "notebook_id": self.notebook.id,
            "cell_type": "sql",
            "input_source": "SELECT 1",
            "sequence": 10,
        })
        self.python_cell = self.env["devops.notebook.cell"].create({
            "notebook_id": self.notebook.id,
            "cell_type": "python",
            "input_source": "import pandas as pd\nassert isinstance(_, pd.DataFrame)\nprint(_.to_dict())",
            "sequence": 20,
        })

    def test_sql_to_pandas_variable(self):
        # Mock _exec_sql to return structured data
        # We patch the method on the class
        with patch("odoo.addons.project_notebook.models.devops_notebook.DevOpsNotebookCell._exec_sql") as mock_exec_sql:
            mock_exec_sql.return_value = {
                "text": "id\n1",
                "html": "<table>...</table>",
                "data": [{"id": 1}, {"id": 2}],
            }
            
            # Run the notebook
            self.notebook.action_run_all()
            
            # Check if python cell succeeded
            self.assertEqual(self.python_cell.status, "success", f"Python cell failed with output: {self.python_cell.output_text}")
            # Check output contains the dictionary representation
            # DataFrame.to_dict() default is 'dict' (column -> {index -> value})
            # [{"id": 1}, {"id": 2}] -> DataFrame
            #    id
            # 0   1
            # 1   2
            # to_dict() -> {'id': {0: 1, 1: 2}}
            self.assertIn("'id': {0: 1, 1: 2}", self.python_cell.output_text)
