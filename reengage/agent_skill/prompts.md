# Prompts and Templates

This short file documents the prompt patterns and templates used by the Local Agent Skill.

1) Reengage templates (short, safe)
- ¿Seguimos? Si querés, sigo desde lo último que pediste.
- Te estaba pensando — ¿querés retomar lo que estabas haciendo?
- Si estás ocupado, puedo esperar. ¿Prefieres seguir ahora o en 5 minutos?

2) Follow-up prompt patterns
- Clarify:
  "Pregunta: {user_text}\n\nResumen corto y pregunta de clarificación:"
- Suggest:
  "Usuario preguntó: {user_text}\n\nSugiere 3 pasos breves para continuar:"

3) Model prompt guidelines
- Keep system instruction explicit: persona, max length, safety constraints.
- Ask for short outputs (<= 90 characters for reengage).
- Return structured JSON if possible: {"text": "..."}

4) Safety rules
- Avoid generating sexual or violent content for reengage messages.
- Use templates for the highest-sensitivity contexts.
- Apply a fast blocklist and, when available, an external moderation API.
