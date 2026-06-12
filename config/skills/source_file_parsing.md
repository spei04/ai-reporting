# Source File Parsing Skill

Use this skill when the user asks what is in an uploaded workbook, CSV, contract, policy, or support file, or when the workflow needs source data normalized before reporting output.

Workflow:
- Identify file type, sheets/tables, headers, periods, and likely reporting use.
- Summarize the source structure in business terms.
- Map source data into standard reporting concepts when possible.
- Preserve uncertainty when sheet names, sign conventions, or headers are ambiguous.

Required inputs:
- Uploaded file or prior session file reference.
- Requested target workflow if the user wants standardization for SCF, filing, support, or evidence.

Output style:
- List detected tables or sheets.
- Explain what can be used directly and what needs mapping.
- Ask for missing files only when required.

Common failure modes:
- Dumping raw rows instead of compressed table summaries.
- Inferring accounting meaning from a label without corroborating support.
- Losing period context, especially QTD vs YTD.
