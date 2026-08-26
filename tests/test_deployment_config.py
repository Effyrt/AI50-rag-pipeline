"""Deployment configuration tests.

Guards the properties that keep the deployment inside GCP's always-free allowances,
and the two regressions that previously hid failures in the deploy scripts.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GCP_DIR = REPO_ROOT / "gcp"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def shell_scripts() -> list[Path]:
    return sorted(GCP_DIR.glob("*.sh"))


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


class TestDeployScriptHygiene:
    @pytest.mark.parametrize("path", shell_scripts(), ids=lambda p: p.name)
    def test_no_error_masking(self, path):
        """`gcloud ... || echo "already exists"` reported failures as success.

        Only that pattern is an offence. `|| echo <default>` used to supply a fallback
        value inside a command substitution is legitimate and not flagged.
        """
        offenders = [
            line.strip()
            for line in path.read_text().splitlines()
            if "|| echo" in line
            and not line.strip().startswith("#")
            and ("already exists" in line or "exists" in line.split("|| echo")[1])
        ]
        assert not offenders, f"{path.name} masks errors: {offenders}"

    @pytest.mark.parametrize("path", shell_scripts(), ids=lambda p: p.name)
    def test_no_public_bucket_grant(self, path):
        offenders = [
            line.strip()
            for line in path.read_text().splitlines()
            if "allUsers" in line and not line.strip().startswith("#")
        ]
        assert not offenders, f"{path.name} grants public access: {offenders}"

    @pytest.mark.parametrize("path", shell_scripts(), ids=lambda p: p.name)
    def test_uses_set_e(self, path):
        assert "set -e" in path.read_text(), f"{path.name} does not use `set -e`"

    def test_no_composer_v1_flags(self):
        """--python-version and --web-server-machine-type are Composer 1 flags."""
        source = (GCP_DIR / "setup_composer.sh").read_text()
        for flag in ("--python-version", "--web-server-machine-type"):
            active = [
                line for line in source.splitlines()
                if flag in line and not line.strip().startswith("#")
            ]
            assert not active, f"Composer 1 flag {flag} still active: {active}"

    def test_cloud_run_jobs_use_task_timeout(self):
        """Cloud Run *Jobs* take --task-timeout; --timeout is a services flag."""
        source = (GCP_DIR / "build_and_deploy.sh").read_text()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "--timeout=" not in stripped:
                continue
            # --timeout is legitimate on `gcloud run deploy` (services).
            assert "--task-timeout=" in stripped or "deploy" in source.split(stripped)[0][-400:], (
                f"bare --timeout on what looks like a job: {stripped}"
            )


class TestCloudRunServices:
    """Lab 10: FastAPI + Streamlit hosted on GCP, within the free tier."""

    @pytest.fixture
    def deploy_script(self) -> str:
        return (GCP_DIR / "build_and_deploy.sh").read_text()

    def test_deploys_both_services(self, deploy_script):
        assert "gcloud run deploy ai50-api" in deploy_script
        assert "gcloud run deploy ai50-ui" in deploy_script

    def test_services_scale_to_zero(self, deploy_script):
        """--min-instances=0 is what keeps the services inside the free tier."""
        assert deploy_script.count("--min-instances=0") >= 2

    def test_services_capped(self, deploy_script):
        """A max-instances cap prevents a traffic spike leaving the free tier."""
        assert deploy_script.count("--max-instances=") >= 2

    def test_ui_receives_api_url(self, deploy_script):
        """The UI must be told where the API is, not left on localhost."""
        assert "API_BASE=${API_URL}" in deploy_script
        assert "status.url" in deploy_script

    def test_api_deployed_before_ui(self, deploy_script):
        """The UI deploy depends on the API URL existing."""
        assert deploy_script.index("gcloud run deploy ai50-api") < deploy_script.index(
            "gcloud run deploy ai50-ui"
        )

    def test_streamlit_has_session_affinity(self, deploy_script):
        """Streamlit's WebSocket needs a stable instance."""
        assert "--session-affinity" in deploy_script


def requirement_names(path: Path) -> set[str]:
    """Package names from a requirements file, ignoring comments and pins."""
    names = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        names.add(line.split("==")[0].split(">=")[0].split("[")[0].strip().lower())
    return names


class TestServiceImages:
    def test_api_image_excludes_scraping_stack(self):
        """The API never scrapes; Playwright/Selenium would bloat the image."""
        reqs = requirement_names(REPO_ROOT / "requirements-api.txt")
        for pkg in ("playwright", "selenium", "webdriver-manager"):
            assert pkg not in reqs, f"{pkg} does not belong in the API image"

    def test_api_uses_cpu_only_torch(self):
        """CUDA wheels add ~2 GB for GPUs Cloud Run does not provide."""
        dockerfile = (REPO_ROOT / "docker" / "Dockerfile.api").read_text()
        assert "download.pytorch.org/whl/cpu" in dockerfile

    def test_ui_image_is_minimal(self):
        """The UI is an HTTP client and needs none of the heavy runtime stack."""
        reqs = requirement_names(REPO_ROOT / "requirements-ui.txt")
        for pkg in ("langchain", "chromadb", "sentence-transformers", "torch", "openai"):
            assert pkg not in reqs, f"{pkg} does not belong in the UI image"

    @pytest.mark.parametrize("name", ["Dockerfile.api", "Dockerfile.ui"])
    def test_image_honours_cloud_run_port(self, name):
        """Cloud Run injects $PORT and requires the container to listen on it."""
        dockerfile = (REPO_ROOT / "docker" / name).read_text()
        assert "${PORT}" in dockerfile, f"{name} ignores $PORT"

    @pytest.mark.parametrize(
        "config,image",
        [("cloudbuild.api.yaml", "ai50-api"), ("cloudbuild.ui.yaml", "ai50-ui")],
    )
    def test_cloudbuild_targets_right_dockerfile(self, config, image):
        spec = yaml.safe_load((GCP_DIR / config).read_text())
        assert any(image in i for i in spec["images"])


class TestWorkflows:
    @pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
    def test_workflow_is_valid_yaml(self, path):
        spec = yaml.safe_load(path.read_text())
        assert "jobs" in spec
        # PyYAML parses the `on:` key as boolean True.
        assert "on" in spec or True in spec

    def test_dag_validation_workflow_exists(self):
        assert (WORKFLOWS / "dag-validation.yml").is_file()

    def test_dag_validation_uses_airflow_constraints(self):
        """Without the constraint file, an Airflow install is not reproducible."""
        source = (WORKFLOWS / "dag-validation.yml").read_text()
        assert "constraints-" in source
        assert "apache-airflow-providers-google" in source

    def test_dag_validation_gates_on_import_errors(self):
        source = (WORKFLOWS / "dag-validation.yml").read_text()
        assert "dags list-import-errors" in source

    def test_dag_validation_uploads_evidence(self):
        """The artifacts are the point: they are the Lab 2/3 run evidence."""
        source = (WORKFLOWS / "dag-validation.yml").read_text()
        assert "upload-artifact" in source

    def test_secret_not_interpolated_into_shell(self):
        """A secret passed via env never appears in a command line."""
        source = (WORKFLOWS / "dag-validation.yml").read_text()
        assert "echo '${{ secrets.GCP_SA_KEY }}'" not in source
        assert "env.HAS_GCP_KEY" in source

    def test_ci_runs_without_credentials(self):
        source = (WORKFLOWS / "ci.yml").read_text()
        assert "requirements-dev.txt" in source
        assert "pytest" in source
