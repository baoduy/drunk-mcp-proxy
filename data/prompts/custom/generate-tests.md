---
description: Generate test cases for a function with specified coverage
role: assistant
parameters:
  function_name: str
  language: str
  num_tests: int
---
Generate {num_tests} comprehensive test cases for the {language} function '{function_name}'.

Include test cases for:
- Happy path scenarios
- Edge cases
- Error conditions
- Boundary values

Use the appropriate testing framework for {language}.
