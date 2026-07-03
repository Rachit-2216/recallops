export const PUBLIC_CASE_STUDY = {
  incidentId: "CF-OUTAGE-2025-12-05",
  recallQuestion:
    "How is the December 5 outage related to the November 18 outage?",
  sources: [
    {
      label: "December 5 outage postmortem",
      href: "https://blog.cloudflare.com/5-december-2025-outage/",
    },
    {
      label: "November 18 outage postmortem",
      href: "https://blog.cloudflare.com/18-november-2025-outage/",
    },
    {
      label: "Code Orange: Fail Small",
      href: "https://blog.cloudflare.com/fail-small-resilience-plan-uk-ua/",
    },
  ],
} as const;
