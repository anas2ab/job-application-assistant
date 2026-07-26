GREENHOUSE_COMPANIES = {
    "OpenAI": "openai",
    "Stripe": "stripe",
    "Datadog": "datadog",
    "Coinbase": "coinbase",
    "Plaid": "plaid",
    "Vercel": "vercel",
    "Notion": "notion",
    "Canva": "canva",
    "Figma": "figma",
    "Ramp": "ramp",
    "HashiCorp": "hashicorp",
    "Cloudflare": "cloudflare",
    "Snyk": "snyk",
    "Cockroach Labs": "cockroachlabs",
    "Confluent": "confluent",
    "ClickHouse": "clickhouse",
    "Scale AI": "scaleai",
    "Elastic": "elastic",
    "MongoDB": "mongodb",
    "GitLab": "gitlab",
    "Robinhood": "robinhood",
    "Reddit": "reddit",
    "PagerDuty": "pagerduty",
    "Instacart": "instacart",
    "Dropbox": "dropbox",
    "Twilio": "twilio",
    "StackAdapt": "stackadapt",
    "Okta": "okta",
}

LEVER_COMPANIES = {
    "Netflix": "netflix",
    "Discord": "discord",
    "Brex": "brex",
    "Miro": "miro",
    "Rippling": "rippling",
    "Zapier": "zapier",
    "Calm": "calm",
    "Faire": "faire",
    "PostHog": "posthog",
    "Render": "render",
    "Sentry": "sentry",
    "Vanta": "vanta",
    "Amplitude": "amplitude",
    "Abnormal AI": "abnormalsecurity",
    "Samsara": "samsara",
    "Glean": "gleanwork",
    "Retool": "retool",
    "Cockroach Labs": "cockroachlabs",
    "Lattice": "lattice",
    "Gusto": "gusto",
    "Highspot": "highspot",
    "CSC Generation": "cscgeneration-2",
    "Air-tek": "air-tek",
    "Deep Sky": "deepsky",
    "PointClickCare": "pointclickcare",
    "RAVL": "ravl_io",
    "Waabi": "waabi",
    "PocketHealth": "PocketHealth",
}

# Public Ashby job board names, verified against the posting API.
ASHBY_COMPANIES = {
    "OpenAI": "openai",
    "Notion": "notion",
    "Ramp": "ramp",
    "Linear": "linear",
    "Cursor": "cursor",
    "Perplexity": "perplexity",
    "Clerk": "clerk",
    "Supabase": "supabase",
    "Deel": "deel",
}

# Company identifiers from public SmartRecruiters career pages.
SMARTRECRUITERS_COMPANIES = {
    "Procore Technologies": "ProcoreTechnologies",
    "Arista Networks": "AristaNetworks",
    "Ample Insight": "ampleinsightinc",
    "Dalstrong": "dalstrong",
    "FZ Engineering": "FZEngineering",
}

# Workday public career-site adapters. Each site has its own tenant and board.
WORKDAY_COMPANIES = {
    "Autodesk": {
        "host": "https://autodesk.wd1.myworkdayjobs.com",
        "tenant": "autodesk",
        "site": "Ext",
    },
    "Thomson Reuters": {
        "host": "https://thomsonreuters.wd5.myworkdayjobs.com",
        "tenant": "thomsonreuters",
        "site": "External_Career_Site",
    },
    "Sun Life": {
        "host": "https://sunlife.wd3.myworkdayjobs.com",
        "tenant": "sunlife",
        "site": "Experienced-Jobs",
    },
}
