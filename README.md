# story_polisher

## Part 0: What this app is

`story_polisher` is a small FastAPI service. You send it a rough feature idea (`POST /polish`) and it sends back a tidy user story
with acceptance criteria and open questions, written by Gemini on Vertex AI. The app is already built and tested. Your job is to get
it running in a GitLab pipeline (Part 1) and, in Week 6, deploy it to Cloud Run (Part 2).

> 📌 **Note**
>
> Commands in this guide use angle brackets for the parts you replace, like `<your_username>`. Do not type the brackets.

**Run it locally with no GCP.** With no project configured, `/polish` returns a canned example marked `"source": "fallback"`, so
the app works on any laptop and in CI.

```bash
poetry install
poetry run python main.py
```

Open <http://localhost:8080/docs>. FastAPI's `/docs` page is the interface: open `POST /polish`, choose **Try it out**, and run it.
`GET /health` returns `{"status": "ok"}`.

**Run it locally with Gemini.** This needs a GCP project with Vertex AI enabled and Application Default Credentials
(`gcloud auth application-default login`). No API key, no key file.

```bash
GOOGLE_CLOUD_PROJECT=<your_project_id> poetry run python main.py
```

Optional settings: `GOOGLE_CLOUD_LOCATION` (default `global`), `GEMINI_MODEL` (default `gemini-3.1-flash-lite`), `PORT` (default `8080`).

**Run the tests.** They use a fake Gemini, so they need no credentials and no network.

```bash
poetry run pytest
```

> 💡 **Tip**
>
> You do not need Docker on your laptop. The pipeline builds the Docker image on GitLab's servers. If you do have Docker,
> `docker build -t story_polisher .` and `docker run -p 8080:8080 story_polisher` run the same image locally.

---

## Part 1: Push to GitLab and get the pipeline green (ICE 6 / OE 3)

### 1. Before you start
- A GitLab.com account with two-factor authentication on (Prep 7).
- **Identity verification.** GitLab.com may ask new free accounts to verify themselves (a phone number or a card; GitLab does not
  charge the card) before their pipelines can use GitLab's shared runners. This is anti-abuse, not a problem with your code.
  If it applies to you and you skipped it, your pipeline fails or never starts and shows a message like
  *"The pipeline failed due to the user not being verified"* or *"identity verification required, until then shared runners
  will be unavailable."* Open **Build → Pipelines** in your project and follow the prompt to verify, then run the pipeline again.

> 📌 **Note**
>
> GitLab changes this requirement from time to time. If the prompt looks different from what is described here, follow what GitLab
> shows you and tell the instructors.

### 2. Clone the template from GitHub
Create your repo from the `tmpl_ice6` template in the `mis-devops-purdue` organization (**Use this template → Create a new repository**,
owner `mis-devops-purdue`). Name it `fa26_ice6_<your_purdue_username>`. Then clone it:

```bash
git clone <your_github_repo_url>
cd <your_repo_folder>
```

### 3. Create a blank GitLab project
In GitLab, choose **Create new project → Create blank project**.
- Project name: `story_polisher`
- Namespace: your own personal namespace (your username)
- Visibility: **Private**
- **Uncheck** "Initialize repository with a README". The project must be empty, or your first push will conflict.

### 4. Add GitLab as a second remote and push
A git repo can have any number of remotes. Each remote is just a name for a URL you can push to. Your clone already has one, `origin`
(GitHub). You will add a second, `gitlab`, so the same code lives in both places and each platform does its own job: GitHub for the
course, GitLab for the pipeline.

```bash
git remote add gitlab <your_gitlab_project_https_url>
git remote -v
git push gitlab main
```

> ⚠️ **Warning**
>
> GitLab does not accept your account password for pushing over HTTPS. When asked for a password, paste a **personal access token**
> (GitLab → your avatar → Preferences → Personal access tokens, scope `write_repository`). Treat it like a password and never commit it.

### 5. Find the pipeline and read the log
Your push to `main` started a pipeline. In your GitLab project open **Build → Pipelines**, then click the pipeline, then each job
(`test`, `build`) to read its log.

**What a green run looks like:**
- Two jobs in order: `test`, then `build`, each with a green check.
- The `test` log ends with `7 passed`.
- The `build` log ends with a line like `Successfully built` or `naming to docker.io/library/story_polisher`.
- The pipeline status at the top says **passed**.

A pipeline takes about two to four minutes the first time. Open `.gitlab-ci.yml` next to the logs and match each block to what you
see: every block has a comment explaining it.

### 6. Break it on purpose
1. In `tests/test_main.py`, change an expected value (for example, change `"ok"` in `test_health_returns_ok` to `"nope"`).
2. Commit and push: `git commit -am "Break a test on purpose"` then `git push gitlab main`.
3. Watch the pipeline fail. The `test` job is red and the `build` job never runs, because it depends on `test` passing.
4. Open the `test` log and find the line that names the failing test and shows `expected` against `actual`.
5. Change the value back, commit, and push. The pipeline goes green again.

### 7. Troubleshooting
| What you see | What it means | Fix |
| --- | --- | --- |
| Pipeline fails or never starts; message about verification or "no runners" | GitLab hasn't verified your account for shared runners | Build → Pipelines → follow the verification prompt, then re-run |
| `remote: HTTP Basic: Access denied` or a 2FA error on push | HTTPS pushes need a personal access token when 2FA is on | Create a token (scope `write_repository`) and paste it as the password |
| `fatal: ... rejected ... fetch first` or "refusing to merge unrelated histories" | The GitLab project wasn't empty (a README was added) | Make a new blank project without a README, or ask for help |
| You pushed but the pipeline never shows up | You pushed to `origin` (GitHub) instead of `gitlab` | `git push gitlab main` |
| `test` job fails on `poetry install` | `pyproject.toml` and `poetry.lock` disagree | Run `poetry lock` locally, commit both files, push |

> 💡 **Tip**
>
> Stuck? Work down this list. (1) Read the failing job's log and look for the first red error line. (2) Paste the log or the pipeline URL
> in the course channel or bring it to office hours. (3) Only if you are still stuck, invite `@robpurdue` and `@akboudh` to your project:
> **Manage → Members → Invite members**, role **Reporter**. (4) When you are done, you may remove them from the same page.

---

## Part 2: Deploy to Cloud Run with Workload Identity Federation (Week 6, ungraded)

In Part 1 your pipeline built and tested the app. Now you will add a `deploy` stage that ships it to Cloud Run, where it calls Gemini
through Vertex AI. You will do this **without any service account key**.

### Two identities
- **The pipeline's identity** deploys the app. GitLab gives each job a short-lived signed token, and Google's Workload Identity
  Federation (WIF) trades it for temporary Google credentials. It is allowed to deploy, and nothing else.
- **The service's runtime identity** is a separate service account the running app uses to call Gemini. It has only the
  **Vertex AI User** role.

Keeping them apart means a problem with the pipeline can't call Gemini as the app, and a problem in the app can't redeploy itself.

> ❗ **Important**
>
> Never create or download a service account key (a `.json` file) for this. If a tutorial tells you to, it is the older approach.
> Our pipeline needs no secrets at all.

Set these shell variables once so the commands below can be copied. Replace the values (no brackets):

```bash
export PROJECT_ID=<your_gcp_project_id>
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export REGION=us-central1
export GITLAB_PATH=<your_gitlab_username>/story_polisher
export POOL_ID=gitlab-pool
export PROVIDER_ID=gitlab-provider
gcloud config set project $PROJECT_ID
```

### 1. Enable the APIs
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
```

### 2. Create the runtime service account
```bash
gcloud iam service-accounts create story-polisher-runtime --display-name="story_polisher runtime"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:story-polisher-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 3. Set up Workload Identity Federation for your GitLab project
Create a pool, then a provider that trusts GitLab.com tokens, but only for your project and the `main` branch.

```bash
gcloud iam workload-identity-pools create $POOL_ID --location=global --display-name="GitLab"

gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --location=global --workload-identity-pool=$POOL_ID \
  --issuer-uri="https://gitlab.com" \
  --allowed-audiences="https://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}" \
  --attribute-mapping="google.subject=assertion.sub,attribute.project_path=assertion.project_path,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.project_path=='${GITLAB_PATH}' && assertion.ref=='main'"
```

> ⚠️ **Warning**
>
> The attribute condition is what stops someone else's GitLab project from deploying to your GCP project. Do not skip it, and do not
> loosen it to a wildcard.

### 4. Give the pipeline identity only the roles it needs
```bash
PRINCIPAL="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.project_path/${GITLAB_PATH}"

gcloud projects add-iam-policy-binding $PROJECT_ID --member="$PRINCIPAL" --role="roles/run.sourceDeveloper"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="$PRINCIPAL" --role="roles/serviceusage.serviceUsageConsumer"

# May act as the runtime service account, and only that one
gcloud iam service-accounts add-iam-policy-binding \
  story-polisher-runtime@${PROJECT_ID}.iam.gserviceaccount.com \
  --member="$PRINCIPAL" --role="roles/iam.serviceAccountUser"

# Cloud Build builds your container; its default service account needs the Cloud Run Builder role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/run.builder"
```

### 5. Add the GitLab variables
In GitLab: **Settings → CI/CD → Variables → Add variable** (type *Variable*, not file; leave "Protect" and "Mask" off, none are
secret). Add:

| Key | Value |
| --- | --- |
| `GCP_PROJECT_ID` | your project ID |
| `GCP_PROJECT_NUMBER` | your project number (`echo $PROJECT_NUMBER`) |
| `GCP_REGION` | `us-central1` (the same as `$REGION`) |
| `WIF_POOL_ID` | `gitlab-pool` |
| `WIF_PROVIDER_ID` | `gitlab-provider` |
| `RUNTIME_SA_EMAIL` | `story-polisher-runtime@<your_project_id>.iam.gserviceaccount.com` |

### 6. Add the `deploy` job
Edit `.gitlab-ci.yml`: change `stages` to `test`, `build`, `deploy`, and add this block at the bottom.

```yaml
# Deploy job: runs only on main, signs in with a short-lived GitLab token (no key file), and deploys to Cloud Run.
deploy:
  stage: deploy
  image: gcr.io/google.com/cloudsdktool/google-cloud-cli:stable
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  id_tokens:
    GITLAB_OIDC_TOKEN:    # GitLab signs this token for this job; Google checks it against your provider
      aud: https://iam.googleapis.com/projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/providers/${WIF_PROVIDER_ID}
  script:
    - echo "$GITLAB_OIDC_TOKEN" > "$CI_PROJECT_DIR/.oidc_token"
    - >
      gcloud iam workload-identity-pools create-cred-config
      projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/providers/${WIF_PROVIDER_ID}
      --credential-source-file="$CI_PROJECT_DIR/.oidc_token" --credential-source-type=text
      --output-file="$CI_PROJECT_DIR/.wif_config.json"
    - gcloud auth login --cred-file="$CI_PROJECT_DIR/.wif_config.json"
    - >
      gcloud run deploy story-polisher
      --source .
      --project "$GCP_PROJECT_ID"
      --region "$GCP_REGION"
      --service-account "$RUNTIME_SA_EMAIL"
      --max-instances 1
      --set-env-vars "GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID},GEMINI_MODEL=gemini-3.1-flash-lite"
      --allow-unauthenticated
      --quiet
```

> 📌 **Note**
>
> `--max-instances 1` caps how much the service can scale, which also caps what a runaway test could cost.

The `--allow-unauthenticated` flag makes the service public, which is acceptable here because of the guardrails (one instance, capped tokens, a 500-character input limit) and because you shut the service down afterward.

Cloud Run service names allow lowercase letters, digits and hyphens only, so this service is `story-polisher` (with a hyphen).

### 7. Push and verify
```bash
git add .gitlab-ci.yml
git commit -m "Add deploy stage"
git push gitlab main
```
Open **Build → Pipelines**. All three jobs should go green. The end of the `deploy` log prints a `Service URL`. Then:

```bash
curl <service_url>/health
curl -X POST <service_url>/polish -H "Content-Type: application/json" -d '{"idea": "let artists upload a show poster"}'
```
The second response should say `"source": "gemini"`. You can also open `<service_url>/docs` in a browser.

### 8. Shut it down afterward
Follow the course guide **Shutting Down Your Cloud Run Service** when you are done, so the service stops accruing cost.

### Common failure messages
| Message | What it means |
| --- | --- |
| `Permission 'run.services.create' denied` or `PERMISSION_DENIED` during deploy | The pipeline identity is missing a role (step 4), or the role was granted a minute ago and hasn't propagated. Re-check the bindings and re-run |
| `Permission 'iam.serviceaccounts.actAs' denied` | The pipeline identity lacks **Service Account User** on the runtime service account (step 4, third command) |
| `403` / `Permission denied` from Vertex AI when you call `/polish` (response is a 502) | The runtime service account is missing **Vertex AI User** (step 2), or the Vertex AI API isn't enabled |
| `404 ... model ... not found` or "publisher model not found in location" | `GEMINI_MODEL` is wrong or not available in that location. Keep `GOOGLE_CLOUD_LOCATION` unset (defaults to `global`) and check the model ID |
| `The given credential is rejected by the attribute condition` | WIF attribute mismatch: the `GITLAB_PATH` in your condition doesn't exactly match your project path, or you pushed from a branch other than `main` |
| `The audience in ID Token ... does not match the expected audience` | The `aud` in `.gitlab-ci.yml` doesn't match the provider's allowed audience. Check the project number, pool ID and provider ID variables |
| `Cannot create ... Artifact Registry` or `run.builder` errors during the build step | The Cloud Build service account is missing **Cloud Run Builder** (step 4, last command) |
