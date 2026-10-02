# Agent Skill: local expert for Elena/Remi

This folder contains a small, local "skill" implementation that serves as a
minimal agent to produce proactive messages (reengage) and short replies using
either templates or a local model endpoint.

Files:
- skill.py: AgentSkill class and a CLI runner to simulate idle/reply behavior

Design goals:
- Minimal: can be run locally without external services (except Redis)
- Safe: simple blocklist filtering and metrics logging to Redis
- Extensible: replace generate_via_model() with your model's API

How to use (quick):

```bash
cd /home/mpeadmin/karukren/remi-ai/reengage
source .venv/bin/activate
python -m reengage.agent_skill.skill --session user-dev-1 --mode idle
```

This prints the payload that would be sent as a reengage message.

Integration notes:
- When ready, wire the payload into the presence_app send flow (POST /internal/send_reengage)
- To personalize, ensure `meta:{session_id}` in Redis includes `user_name` and `last_user_msg`
