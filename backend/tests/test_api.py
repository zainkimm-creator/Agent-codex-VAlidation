from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_health_and_equations_routes():
    assert client.get("/health").json() == {"status": "ok"}
    equations = client.get("/equations").json()
    assert equations["state_vector"] == "x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]"
    backend_equations = equations["backend_equations"]
    assert len(backend_equations) >= 10
    equation_text = " ".join(item["equation"] for item in backend_equations)
    assert "v_i = R_i * omega_i" in equation_text
    assert "domega_i/dt" in equation_text
    assert "RMSE_theta" in equation_text
    paper_equations = equations["paper_equations"]
    assert len(paper_equations) >= 9
    paper_text = " ".join(item["equation"] for item in paper_equations)
    assert "dT_i/dt" in paper_text
    assert "J_multi" in paper_text
    assert len(equations["equation_register"]) == len(paper_equations) + len(backend_equations)
    assert len(equations["theory_summary"]) >= 5


def test_plants_route_returns_ten_supplement_plants():
    response = client.get("/plants")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_plant_id"] == "P01"
    assert len(payload["plants"]) == 10
    assert payload["plants"][0]["plant_id"] == "P01"
    assert payload["plants"][-1]["plant_id"] == "P10"


def test_dashboard_outputs_route_returns_required_pages():
    response = client.get("/dashboard/outputs")
    assert response.status_code == 200
    payload = response.json()
    titles = [page["title"] for page in payload["pages"]]
    assert titles == [
        "Plant Setup",
        "Model Equations",
        "Controller",
        "SysID Setup",
        "Logging Validation",
        "Excitation Validation",
        "Noise/LPF Validation",
        "Drift Validation",
        "Retuning Validation",
        "Export Report",
    ]
    logging_page = payload["pages"][4]
    assert "formula" in logging_page
    assert "paper_target" in logging_page
    assert "dashboard_result" in logging_page
    assert logging_page["display_mode"] == "graph"
    assert logging_page["result_points"]
    assert "csv" in logging_page["output_files"]
    assert logging_page["output_files"]["csv"]["url"].endswith("logging_paper_comparison.csv")
    assert logging_page["output_files"]["plot"]["url"].endswith("logging_paper_comparison.svg")

    noise_page = payload["pages"][6]
    assert noise_page["display_mode"] == "table"
    assert noise_page["output_files"]["csv"]["url"].endswith("noise_lpf_paper_comparison.csv")
    retuning_page = payload["pages"][8]
    assert "sum_i w_i" in retuning_page["formula"]


def test_simulate_route_returns_metrics_and_csv_path():
    response = client.post(
        "/simulate",
        json={"plant_id": "P02", "duration_s": 0.5, "log_sample_time_ms": 10, "output_name": "api_test_sim.csv"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "tension_rmse_N" in payload["metrics"]
    assert payload["plant"]["plant_id"] == "P02"
    assert payload["plant"]["applied_parameters"]["EA_N"] == 9600.0
    assert payload["csv_path"].endswith("api_test_sim.csv")
    assert payload["xlsx_path"].endswith("api_test_sim.xlsx")
    assert payload["xlsx_url"].endswith("/data/processed/api_test_sim.xlsx")
    with ZipFile(Path(payload["xlsx_path"])) as workbook:
        sheet_names = set(workbook.namelist())
        shared_strings = workbook.read("xl/sharedStrings.xml").decode("utf-8")
    assert "xl/worksheets/sheet1.xml" in sheet_names
    assert "xl/worksheets/sheet2.xml" in sheet_names
    assert "tension_rmse_N" in shared_strings
    assert "max_overshoot_N" in shared_strings
    assert payload["calculation_summary"]
    assert len(payload["calculations"]) >= 3
    assert len(payload["calculations"][0]["steps"]) >= 5


def test_sysid_route_returns_estimates():
    response = client.post("/sysid", json={"plant_id": "P02", "duration_s": 1.0, "log_sample_time_ms": 10})
    assert response.status_code == 200
    payload = response.json()
    assert "EA" in payload["estimates"]
    assert payload["plant"]["plant_id"] == "P02"
    assert payload["metrics"]["samples"] > 0
    assert payload["calculation_summary"]
    assert len(payload["calculations"]) == 8
    assert len(payload["calculations"][-1]["steps"]) >= 5


def test_invalid_plant_id_returns_400():
    response = client.post("/simulate", json={"plant_id": "P99", "duration_s": 0.2})
    assert response.status_code == 400


def test_validation_routes_return_json_artifacts():
    parts_response = client.get("/validation/parts")
    assert parts_response.status_code == 200
    assert parts_response.json()["parts"][0]["id"] == "part-1"

    part1_response = client.post("/validate/part/1", json={})
    assert part1_response.status_code == 200
    part1_payload = part1_response.json()
    assert part1_payload["metrics"]["parameters_checked"] == 6
    assert part1_payload["metrics"]["out_of_range_count"] == 0
    assert len(part1_payload["comparison_table"]) == 6
    assert len(part1_payload["calculations"]) == 6
    assert len(part1_payload["calculations"][0]["steps"]) >= 5
    assert part1_payload["plot_url"].endswith("part1_parameter_difference.svg")

    logging_response = client.post("/validate/logging-rate", json={"tlog_ms_values": [1, 10, 20]})
    assert logging_response.status_code == 200
    logging_payload = logging_response.json()
    assert logging_payload["metrics"]["supports_noisy_optimum_near_10_20ms"] is True
    assert len(logging_payload["calculations"]) >= 2
    assert logging_payload["plot_url"].endswith("logging_rate_vs_rmse.svg")

    excitation_response = client.post("/validate/excitation", json={})
    assert excitation_response.status_code == 200
    excitation_payload = excitation_response.json()
    assert excitation_payload["metrics"]["supports_multi_channel_or_toggle_under_noise"] is True
    assert len(excitation_payload["calculations"]) >= 2
    assert excitation_payload["plot_url"].endswith("excitation_vs_rmse.svg")

    drift_response = client.post("/validate/drift", json={})
    assert drift_response.status_code == 200
    drift_payload = drift_response.json()
    assert drift_payload["metrics"]["supports_J_drift_dominance"] is True
    assert len(drift_payload["calculations"]) >= 2
    assert drift_payload["plot_url"].endswith("drift_degradation.svg")

    retune_response = client.post("/retune", json={})
    assert retune_response.status_code == 200
    retune_payload = retune_response.json()
    assert retune_payload["metrics"]["supports_HGS_BO5_fewer_real_evaluations_than_CS_BO30"] is True
    assert len(retune_payload["calculations"]) >= 2
    assert "sum_i w_i" in retune_payload["calculations"][0]["formula"]
    assert retune_payload["plot_url"].endswith("retuning_cost.svg")


def test_upload_route_saves_file_to_uploads_folder():
    response = client.post("/upload", files={"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sample.csv"
    assert payload["bytes"] == 8
    assert payload["url"].endswith("/data/uploads/sample.csv")
