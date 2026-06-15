# Reading the scores

Request `custom_fields` in a `findScenes` / `findPerformers` query and sort/rank client-side on
`restash_score`:

```graphql
query {
  findScenes(filter: { per_page: 50 }) {
    scenes { id title custom_fields }
  }
}
```

Custom fields are **filterable** in the Stash UI too, so you can build saved filters (e.g. "fresh
discoveries" where `restash_score` ≥ 90).

!!! warning "Filtering yes, sorting no"
    Stash supports custom-field *filtering* but not *sorting* in the UI, so sort by score via the
    API/client.

See **[What gets written](index.md#what-gets-written)** for the full list of `restash_*` keys and
their types.
