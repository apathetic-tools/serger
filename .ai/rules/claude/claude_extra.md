## AI Model Strategy

When identifying tasks that require complex reasoning, planning, or analysis, ask for confirmation before proceeding:

> "This task appears to require significant planning and reasoning. Would you like me to use a hybrid model approach to create a detailed execution plan first, then switch to a faster model for implementation?"

If confirmed, follow this workflow:
1. **Check model availability**: Determine if the Opus model is available for the Task tool
2. **Planning phase**: 
   - If Claude Opus is available: Use the Task tool with `model: "opus"` and `subagent_type: "general-purpose"` to create a detailed execution plan and document the approach
   - If Claude Opus is not available: Use the Task tool with `model: "sonnet"` and `subagent_type: "general-purpose"` to create a detailed execution plan and document the approach
3. **Execution phase**: After receiving the plan:
   - If Opus was used for planning: Use Claude Sonnet to implement the plan following the documented steps
   - If Sonnet was used for planning: Use Claude Haiku to implement the plan following the documented steps

This hybrid approach combines the most capable model's superior reasoning for complex problems with faster models' speed for straightforward implementation.

