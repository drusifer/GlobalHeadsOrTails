# Bob System - Quick Reference

## TL;DR
The **Bob System** is a single AI that switches between 5 personas (Bob, Neo, Morpheus, Trin, Oracle) based on conversation context.

**How to use**:
1. Type `*chat` - I read the chat log and respond as the appropriate persona
2. Repeat `*chat` - The conversation continues with different personas as needed

## Available Personas & Commands

### 👔 Bob - Prompt Engineering Expert
**Prefix**: `*prompt`, `*reprompt`, `*learn`

| Command | Description |
|---------|-------------|
| `*prompt <DESC>` | Create a new agent prompt |
| `*reprompt <INSTRUCTIONS>` | Update existing agent prompts |
| `*learn <LESSON>` | Broadcast a lesson to all agents |
| `*help` | Show this help message |

---

### 💻 Neo - Senior Software Engineer
**Prefix**: `*swe`

| Command | Description |
|---------|-------------|
| `*swe impl <TASK>` | Implement a feature or function |
| `*swe fix <ISSUE>` | Fix a bug |
| `*swe test <SCOPE>` | Write and run tests |
| `*swe refactor <TARGET>` | Refactor code |

---

### 🧠 Morpheus - Tech Lead / Senior Engineer
**Prefix**: `*lead`

| Command | Description |
|---------|-------------|
| `*lead story <USER_STORY>` | Add/update user story |
| `*lead plan <EPIC>` | Break down epic into tasks |
| `*lead guide <ISSUE>` | Provide architectural guidance |
| `*lead refactor <TARGET>` | Identify code smells and prescribe refactoring |
| `*lead decide <CHOICE>` | Make architectural decision |

---

### 🛡️ Trin - QA / Guardian
**Prefix**: `*qa`

| Command | Description |
|---------|-------------|
| `*qa test <SCOPE>` | Run test suite |
| `*qa verify <FEATURE>` | Create test plan for feature |
| `*qa report` | Summarize codebase health |
| `*qa repro <ISSUE>` | Create minimal reproduction case |

---

### 📚 Oracle - Knowledge Officer / Documentation Architect
**Prefix**: `*ora`

| Command | Description |
|---------|-------------|
| `*ora groom` | Organize file structure |
| `*ora ask <QUESTION>` | Query knowledge base |
| `*ora record <TYPE> <CONTENT>` | Log decision/lesson/risk/assumption |
| `*ora distill <FILE_PATH>` | Break down large document |

---

## Special Commands

### `*chat`
Triggers the Bob System multi-persona workflow:
1. Read chat log
2. Identify next persona
3. Switch to that persona
4. Perform action
5. Post to chat

### `*tell <agent_name> <INSTRUCTION>`
Send a direct message to a persona (adds to `CHAT.md`)

---

## File Locations
- **Agent Definitions**: `bob.docs/*_AGENT.md`
- **Chat Log**: `CHAT.md`
- **Protocol**: `bob.docs/BOB_SYSTEM_PROTOCOL.md`
- **Help**: `bob.docs/HELP.md` (this file)
