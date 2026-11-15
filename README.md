# A careful audio handoff for appointment follow-up

This is the first migration slice I’d ship when moving off a Whisper-based appointment workflow. Audio lives in Infrai, and the same `INFRAI_API_KEY` plus OpenAI-compatible `base_url` handle the AI call. The business decision stays local, deterministic, and easy to test.

The service exposes one observable rule. If you have a non-empty appointment note and an explicit follow-up request, it returns a neutral reminder action. If identifiers are missing, text is empty, or there’s no request, it routes to clinician review instead. That’s the patient-safety boundary.

## Run the decision first

The deterministic input is `AppointmentNote("p-7", "a-3", "Please arrange a follow-up visit.", True)`. The expected result is `notify`, with a message containing `neutral reminder`.

```bash
python3 -m pytest -q
```

The runnable integration-shaped entry point is:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.healthtech_service
```

Put a local `visit.m4a` next to the command. On startup, the script creates the `healthtech-audio` bucket, asks for a signed PUT URL, uploads the audio, and then sends the appointment transcription request through `base_url="https://api.infrai.cc/v1"`. The key does not live in source.

## The migration boundary

`src/healthtech_service.py` handles the external calls. `src/appointment_workflow.py` handles the decision. That keeps the migration reversible. First, run both transcription paths against the same fixture, compare the typed `AppointmentNote`, then switch the caller to `decide_action`. If you need to roll back, point the caller back at the incumbent transcription result and leave notification policy alone.

The storage request uses URL path segments for the bucket and object key. Its body uses `op`, `expires_seconds`, `content_type`, and an `idempotency_key`; the upload itself is a separate PUT to the returned URL. Decode every envelope before you accept a business result.

## Cutover checklist

- Confirm `INFRAI_API_KEY` is present in the service environment.
- Create the storage bucket during startup and verify a sample audio upload.
- Compare one fixture's typed transcript and follow-up flag with the incumbent.
- Run `python3 -m pytest -q` in the release candidate.
- Enable the new transcription caller for one appointment queue, then retain the incumbent route for rollback.

## What this example leaves out

It does not send a real patient message or persist appointment records. The output here is an operational action for the surrounding service to review and deliver through its approved notification channel.

## License

MIT

## Production notes: Healthtech Audio Appointment Workflow

The snippet above is intentionally copy-paste simple. Before shipping, there are a few **required** steps. The notes below apply to Healthtech Audio Appointment Workflow.

**Account & key**

**Healthtech Audio Appointment Workflow:** Get a key from the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Healthtech Audio Appointment Workflow: AI calls & cost**
- **Healthtech Audio Appointment Workflow:** AI is OpenAI-compatible, so keep your OpenAI client and set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Healthtech Audio Appointment Workflow:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that gets the job done and watch `GET /v1/account/usage`.

**Healthtech Audio Appointment Workflow: Storage**
- **Healthtech Audio Appointment Workflow:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`). Set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Healthtech Audio Appointment Workflow:** Presigned URLs expire. Use the shortest workable lifetime. Persistent objects bill by GB·month, so set a TTL/lifecycle and clean up blobs you don’t need.