
| name         | type   | default   | display_name   | editable   | required   | group      | description                                 |
|:-------------|:-------|:----------|:---------------|:-----------|:-----------|:-----------|:--------------------------------------------|
| species      | str    | ""        | Species        | True       | False      | Animal     | Animal species (e.g., mouse, rat).          |
| sex          | str    | ""        | Sex            | True       | False      | Animal     | Biological sex or experimental sex label.   |
| genotype     | str    | ""        | Genotype       | True       | False      | Animal     | Genotype or strain label.                   |
| region       | str    | ""        | Region         | True       | False      | Sample     | Brain region or anatomical location.        |
| cell_type    | str    | ""        | Cell type      | True       | False      | Sample     | Type of cell or vessel being imaged.        |
| depth        | float  | None      | Depth          | True       | False      | Sample     | Imaging depth in micrometers.               |
| branch_order | int    | None      | Branch order   | True       | False      | Sample     | Branch order for vascular structures.       |
| direction    | str    | ""        | Direction      | True       | False      | Sample     | Flow direction or vessel orientation.       |
| condition    | str    | ""        | Condition      | True       | False      | Experiment | Experimental condition or treatment.        |
| condition2   | str    | ""        | Condition 2    | True       | False      | Experiment | Second condition field.                     |
| treatment    | str    | ""        | Treatment      | True       | False      | Experiment | Treatment applied.                          |
| treatment2   | str    | ""        | Treatment 2    | True       | False      | Experiment | Second treatment field.                     |
| date         | str    | ""        | Date           | True       | False      | Experiment | User-editable date (e.g., experiment date). |
| note         | str    | ""        | Note           | True       | False      | Notes      | Free-form notes or comments.                |

*Generated on 260611 14:52:32 · cloudscope v0.1.0*
