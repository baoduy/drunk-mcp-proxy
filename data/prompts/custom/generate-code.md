---
description: Generates a code generation request for a specific programming language
role: assistant
parameters:
  language: str
  task_description: str
---
Write a {language} function that performs the following task: {task_description}

Please include:
- Function signature with proper types
- Docstring explaining the purpose
- Error handling where appropriate
- Example usage
