# Role-Based Access Control (RBAC)

## Permissions Matrix
| Role     | Read Workloads | Edit Policies | Execute Manual Actions | Manage Users |
|----------|----------------|---------------|------------------------|--------------|
| Admin    | Yes            | Yes           | Yes                    | Yes          |
| SRE      | Yes            | Yes           | Yes                    | No           |
| Operator | Yes            | No            | Yes                    | No           |
| Viewer   | Yes            | No            | No                     | No           |