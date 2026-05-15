#!/bin/bash
# Generate TypeScript types from Supabase schema
# Usage: ./scripts/generate-types.sh <project-ref>

if [ -z "$1" ]; then
    echo "Usage: ./scripts/generate-types.sh <supabase-project-ref>"
    exit 1
fi

npx supabase gen types typescript --project-id "$1" > web/src/lib/supabase/types.ts
echo "Types generated at web/src/lib/supabase/types.ts"
