---
description: Request code review with specific focus areas
role: user
parameters:
  code_snippet: str
  language: str
  focus_areas: str
---
Please review the following {language} code:

```{language}
{code_snippet}
```

Focus on these areas: {focus_areas}

Provide feedback on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Suggestions for improvement
