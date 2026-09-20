#!/usr/bin/env python3
"""selftest.py -- offline validation for github-repo-manager.

Runs entirely offline: no network calls, no real tokens, no writes outside a
temporary directory. Prints `PASS x/y` and exits 0 only when everything passes.

Usage:  python selftest.py
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import secret_scan      # noqa: E402
import detect_env       # noqa: E402
import push_repo        # noqa: E402
import publish_audit    # noqa: E402
import update_skill     # noqa: E402
import create_repo      # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def main():
    # --- push_repo: git object hashing (matches `git hash-object`) ----------
    check("blob_sha_empty",
          push_repo.git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
          push_repo.git_blob_sha(b""))
    check("blob_sha_hello",
          push_repo.git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a",
          push_repo.git_blob_sha(b"hello\n"))

    with tempfile.TemporaryDirectory() as td:
        clean = os.path.join(td, "clean.txt")
        with open(clean, "w", encoding="utf-8") as f:
            f.write("hello world\n")
        secret_path = os.path.join(td, "secret.txt")
        with open(secret_path, "w", encoding="utf-8") as f:
            f.write("token = ghp_" + "A" * 36 + "\n")
        envf = os.path.join(td, ".env")
        with open(envf, "w", encoding="utf-8") as f:
            f.write("X=1\n")
        lic = os.path.join(td, "LICENSE")
        with open(lic, "w", encoding="utf-8") as f:
            f.write("MIT License\n\nPermission is hereby granted, free of charge...\n")

        # --- secret_scan -----------------------------------------------------
        f1, _ = secret_scan.scan(td, ["secret.txt"])
        check("scan_detects_github_token",
              any(x["rule"] == "github_token" for x in f1), str(f1))
        f2, _ = secret_scan.scan(td, ["clean.txt"])
        check("scan_clean_passes", len(f2) == 0, str(f2))
        f3, _ = secret_scan.scan(td, [".env"])
        check("scan_detects_env_filename",
              any(x["rule"] == "sensitive_filename" for x in f3), str(f3))
        ig = os.path.join(td, "ignored.txt")
        with open(ig, "w", encoding="utf-8") as f:
            f.write("key = ghp_" + "A" * 36 + "  # secret-scan: ignore\n")
        fi, _ = secret_scan.scan(td, ["ignored.txt"])
        check("scan_ignore_marker", len(fi) == 0, str(fi))
        f4, _ = secret_scan.scan(td, ["clean.txt"])
        check("scan_scanned_count",
              secret_scan.scan(td, ["clean.txt"])[1] == ["clean.txt"], "")

        # --- push_repo.build_plan -------------------------------------------
        plan = push_repo.build_plan(td, ["clean.txt"], {})
        check("plan_create_when_absent", plan[0]["op"] == "create", str(plan))
        sha_clean = push_repo.git_blob_sha(open(clean, "rb").read())
        plan2 = push_repo.build_plan(td, ["clean.txt"],
                                     {"clean.txt": {"type": "blob", "sha": sha_clean}})
        check("plan_unchanged_when_same", plan2[0]["op"] == "unchanged", str(plan2))
        plan3 = push_repo.build_plan(td, ["clean.txt"],
                                     {"clean.txt": {"type": "blob", "sha": "deadbeef"}})
        check("plan_update_when_different", plan3[0]["op"] == "update", str(plan3))
        plan4 = push_repo.build_plan(td, ["nope.txt"], {})
        check("plan_missing_file", plan4[0]["op"] == "missing", str(plan4))

        # --- create_repo payload / empty-repo support -----------------------
        cp = create_repo.build_payload("demo", "desc", True, False, None)
        check("create_repo_payload_private",
              cp == {"name": "demo", "private": True, "auto_init": False,
                     "description": "desc"}, str(cp))
        cp2 = create_repo.build_payload("demo")
        check("create_repo_payload_default_public_empty",
              cp2 == {"name": "demo", "private": False, "auto_init": False}, str(cp2))
        check("create_repo_payload_license",
              create_repo.build_payload("d", license_template="mit").get("license_template") == "mit",
              "")
        check("push_repo_has_branch_head_optional",
              callable(getattr(push_repo, "get_branch_head_optional", None)), "")

        # --- publish_audit ---------------------------------------------------
        aud = publish_audit.audit(td)
        check("audit_detects_license",
              any(l["detected"] == "MIT" for l in aud["licenses"]), str(aud["licenses"]))
        check("audit_flags_env_file", ".env" in aud["credential_files"],
              str(aud["credential_files"]))
        check("audit_blocks_on_credentials", aud["ok"] is False, str(aud["ok"]))
        check("audit_asks_user", len(aud["ask_user"]) > 0, str(aud["ask_user"]))

        # --- publish_audit: suspicious name flag ----------------------------
        bad = os.path.join(td, "keygen.exe")
        with open(bad, "wb") as f:
            f.write(b"MZ")
        aud2 = publish_audit.audit(td)
        check("audit_flags_suspicious_name",
              any("keygen" in c["file"] for c in aud2["community_flags"]),
              str(aud2["community_flags"]))

    # --- detect_env ----------------------------------------------------------
    r = detect_env.detect(".")
    for k in ("git_cli", "git_remote", "docker", "token_env", "api_base",
              "recommended_channel"):
        check("detect_env_has_" + k, k in r, str(sorted(r.keys())))

    # --- need-token signalling (no token in the environment) ----------------
    saved = {k: os.environ.pop(k) for k in ("GH_TOKEN", "GITHUB_TOKEN") if k in os.environ}
    try:
        r3 = detect_env.detect(".")
        check("detect_env_need_token_when_absent", r3.get("need_token") is True,
              str(r3.get("need_token")))
        check("detect_env_next_action",
              r3.get("next_action") == "ask_user_for_token",
              str(r3.get("next_action")))
        check("push_repo_has_prompt_token",
              callable(getattr(push_repo, "prompt_token", None)), "")
        with tempfile.TemporaryDirectory() as td2:
            cf = os.path.join(td2, "clean.txt")
            with open(cf, "w", encoding="utf-8") as f:
                f.write("hi\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = push_repo.main(["--repo", "o/r", "--root", td2,
                                     "--files", "clean.txt", "-m", "t"])
            check("push_repo_no_token_returns_3", rc == 3, str(rc))
            check("push_repo_no_token_asks_user", "ASK THE USER" in buf.getvalue(),
                  buf.getvalue()[:120])
    finally:
        for k, v in saved.items():
            os.environ[k] = v

    # --- update_skill: semver ------------------------------------------------
    check("semver_parse_v_prefix", update_skill.parse_ver("v1.2.3") == (1, 2, 3),
          str(update_skill.parse_ver("v1.2.3")))
    check("semver_parse_short", update_skill.parse_ver("1.0") == (1, 0, 0),
          str(update_skill.parse_ver("1.0")))
    check("semver_newer", update_skill.parse_ver("0.2.0") > update_skill.parse_ver("0.1.0"), "")

    # --- report --------------------------------------------------------------
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    for name, ok, detail in RESULTS:
        line = ("PASS " if ok else "FAIL ") + name
        if not ok:
            line += "  <- " + detail[:140]
        print(line)
    print(f"\nRESULT {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
