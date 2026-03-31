# AGENTS.md file

## Dev environment tips

- Use `just` for all the tasks like lint, test, build, openAPI regen, etc.
- Use plain `just` to simulate a CI run - this needs to pass before commit!

## Testing instructions

- use pytest exclusively
- Add or update tests for the code you change, even if nobody asked.
- ALWAYS add test for ALL API related changes - MUST HAVE!
- Do not only add happy-path tests, but test the most glaring cornercases as well.
- Use pytes's parametrize to cover more ground, if possible stick to the interval testing
- ALWAYS use test factories (factory boy) if possible - or create new ones if missing

## Frontend clean code instructions

- Always create dedicated .vue components whenever an element has more than a single usage
- Always make the interface clean - only props that are needed, 2-way defineModel binding if possible, no prop drilling!
- use exlusively UnoCSS (tailwind style) styling, avoid custom scoped (S)CSS if possible

## Backend clean code instructions

- NO logic in API routes! Implement functionality as methods/functions in a core service or add a new service if required
