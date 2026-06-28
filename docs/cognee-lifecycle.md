# Cognee lifecycle contract

RecallOps maps each visible memory action to one explicit Cognee operation.

| UI action | Cognee operation | Scope | Success claim |
|---|---|---|---|
| Seed/upload evidence | `remember` | permanent dataset + stable data ID | evidence `ready` |
| Add observation | `remember` | server-generated incident session | `session_stored`, never permanent |
| Ask incident memory | `recall` | permanent dataset + current session | `referenced` only with parsed references |
| Confirm resolution | `remember`, then `improve` | exact incident session | `promoted` only after both succeed |
| Forget memory | `forget` | one permanent evidence data ID | `forgotten` only after recall no longer references it |
| Reject hypothesis | no account-wide forget | local/session candidate | rejected locally, not described as provider deletion |

## Remember

Permanent evidence uses the fixed `recallops_evidence_v1` dataset and stable
UUIDv5 IDs. Incident observations use `incident:<incident-id>` sessions.
Provider failures leave observations `pending` with retry identity intact.

## Recall

Recall is scoped to the dataset and current session. RecallOps persists graph
source, Cognee search type, document name, data ID, chunk ID, snippet, and four
human-readable relationship reasons. An answer without references is
`unverified` and cannot enter the verified resolution flow.

## Improve

Improve is not triggered by positive feedback alone. It requires root cause,
mitigation, verification, at least one referenced trace from the same incident,
and human confirmation. RecallOps first remembers a compact verified resolution
in the session, then improves that exact session. Any provider failure keeps the
incident `mitigated` and the resolution `promotion_failed`.

## Forget

Forget is item-level only. The operator must type `FORGET <filename>`. RecallOps
records whether the item was referenced before deletion, asks Cognee to remove
that data ID from graph/vector representations, recalls again, and marks the
item forgotten only if the reference is absent.

RecallOps never invokes account-wide deletion.

## Session deletion limit

Cognee session memory does not expose the same verified item-level deletion
contract used for permanent evidence in this application. **Reject hypothesis**
therefore changes local candidate state and prevents promotion; it does not
claim to delete every provider representation of a session observation.
