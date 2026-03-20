# Example Queries for Prompt Testing

These queries are designed to challenge the V1 prompts and demonstrate areas for improvement.

## Router Prompt Challenges

Looking at ROUTER_PROMPT_V1, it's actually pretty clear:
- DATABASE: "Product stock, inventory, prices, store info"
- POLICY: "General return policy, warranty info"
- CHAT: "Greetings, 'thank you', 'no', 'yes', or casual chatter"

**Realistic failures:**

- "I want to return something I bought last week"
  - **Issue**: Could route to DATABASE (looking for order) instead of POLICY
  - **Why**: Mentions "bought" which suggests order lookup, but user wants return policy
  - **V1 Problem**: Doesn't clarify that return questions should go to POLICY even if they mention purchases

- "Where are your stores located?"
  - **Issue**: Could route to POLICY (general info) instead of DATABASE
  - **Why**: Sounds like a general FAQ question
  - **V1 Problem**: "store info" is under DATABASE but phrasing might confuse router

- "What's your return policy on electronics?"
  - **Issue**: Might route to DATABASE (electronics = products) instead of POLICY
  - **Why**: Mentions product category which could trigger DATABASE routing
  - **V1 Problem**: Doesn't emphasize that policy questions go to POLICY regardless of product mention

## SQL Prompt Challenges

Looking at SQL_SYSTEM_PROMPT_V1:
- Mentions filtering by name/description using LIKE ✓
- Mentions orders need order_id ✓
- **Missing**: Price filtering, JOINs, aggregations, category filtering guidance

**Realistic failures:**

- "What wireless headphones do you have under $100?"
  - **Issue**: Needs price filtering (`WHERE price < 100`)
  - **V1 Problem**: Prompt only mentions filtering by name/description, doesn't mention price filtering
  - **Likely failure**: Might search for "wireless headphones" but not filter by price

- "Which stores have the most inventory?"
  - **Issue**: Needs JOIN between `stores` and `store_inventory`, plus aggregation (SUM, GROUP BY, ORDER BY)
  - **V1 Problem**: Prompt doesn't mention JOINs or aggregations at all
  - **Likely failure**: Might try to query stores table alone, or fail to aggregate properly

- "What products are in my order TECH-001?"
  - **Issue**: Needs JOIN between `orders` and `order_items` tables
  - **V1 Problem**: Prompt says "check the 'orders' table" but doesn't mention joining with order_items
  - **Likely failure**: Might only return order info, not the products in it

- "Show me all gaming accessories"
  - **Issue**: Needs to filter by `category = 'Gaming'` or search category field
  - **V1 Problem**: Prompt says "filter by name/description" but doesn't mention category field
  - **Likely failure**: Might search description for "gaming" instead of using category field

- "Do you have any 65 inch TVs in stock?"
  - **Issue**: Needs to search product name/description for "65 inch" AND check `in_stock` field
  - **V1 Problem**: Prompt mentions LIKE for name/description but doesn't mention checking `in_stock` field
  - **Likely failure**: Might find TVs but not filter by stock status

## RAG Prompt Challenges

Looking at RAG_SYSTEM_PROMPT_V1:
- Very minimal: "You are a policy assistant. Use the handbook to answer questions."
- Tool description: "Search policy handbook for relevant information."

**Realistic failures:**

- "Can I get my money back?"
  - **Issue**: User means "return" but uses different phrasing
  - **V1 Problem**: Tool description is generic, doesn't guide LLM to expand search terms
  - **Likely failure**: RAG search for "money back" might not match "return policy" content

- "What if my product breaks within a year?"
  - **Issue**: User asking about warranty but phrasing as conditional question
  - **V1 Problem**: Prompt doesn't guide LLM to extract key terms ("warranty", "breaks") for search
  - **Likely failure**: Search query might be too literal ("product breaks within a year") instead of searching for "warranty"

- "How long do returns take?"
  - **Issue**: Needs to find return policy AND shipping/processing time info
  - **V1 Problem**: Single search might not capture both concepts
  - **Likely failure**: Might find return policy but miss processing time details

## Chat Prompt Challenges

Looking at CHAT_SYSTEM_PROMPT_V1:
- Very minimal: "You are a helpful customer support assistant for Ohm Sweet Ohm. Be polite and concise."

**Realistic failures:**

- "Thanks for your help earlier"
  - **Issue**: References previous conversation but history might be empty
  - **V1 Problem**: No guidance on handling missing context
  - **Likely failure**: Might respond awkwardly or ask what they're thanking for

- "That's not what I asked"
  - **Issue**: User is correcting the agent
  - **V1 Problem**: No guidance on handling corrections or clarifications
  - **Likely failure**: Might apologize but not ask what they actually wanted

## Multi-Step Queries (Router Limitation)

- "I want to return my order, but first tell me what was in it"
  - **Issue**: Needs both DATABASE (order items) and POLICY (return policy)
  - **V1 Problem**: Router can only pick one category - this is a fundamental limitation
  - **Likely failure**: Will route to one category and miss the other part

## Recommended Demo Flow

1. **Start with V1 prompts** - Run these queries and show failures in Opik
2. **Identify patterns** - Group failures by type (routing, SQL, RAG, etc.)
3. **Create V2 prompts** - Address the specific failure patterns:
   - Add price filtering guidance to SQL prompt
   - Add JOIN and aggregation examples to SQL prompt
   - Add category field guidance to SQL prompt
   - Expand RAG tool description to guide better search term extraction
   - Add clarification handling to Chat prompt
4. **Switch to V2** - Change version assignments in `prompts.py`
5. **Re-run same queries** - Show improvements in Opik dashboard

## Quick Test Set (Most Likely to Actually Fail)

1. "What wireless headphones do you have under $100?" - **SQL: Missing price filter**
2. "Which stores have the most inventory?" - **SQL: Missing JOIN/aggregation**
3. "What products are in my order TECH-001?" - **SQL: Missing JOIN guidance**
4. "Can I get my money back?" - **RAG: Phrasing mismatch**
5. "I want to return something I bought last week" - **Router: Ambiguous routing**
