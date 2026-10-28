"""End-to-end behavior tests for the skill-only installation path.

These tests exercise the real ``superwiki-init`` and ``skills.sh`` scripts in
isolated temporary directories.  They assert filesystem behavior (symlinks,
preserved content, rejected options) rather than script text.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "superwiki-init"
BASH = "/bin/bash"

RUNTIME_LINKS = (
    (".agents", ".agents/skills"),
    (".opencode", ".opencode/skills"),
    (".claude", ".claude/skills"),
    (".cursor", ".cursor/skills"),
)

# ``skills.sh`` links SuperWiki only into the agent-compatible skill dir.
GLOBAL_SKILL_DIRS = (Path(".agents") / "skills",)

# Runtime-specific global skill dirs that ``skills.sh`` must never create links in.
OTHER_GLOBAL_SKILL_DIRS = (
    Path(".config") / "opencode" / "skills",
    Path(".claude") / "skills",
    Path(".codex") / "skills",
    Path(".cursor") / "skills",
)


def make_dist(root: Path) -> Path:
    """Create an installable copy of the real SuperWiki skill (no agents)."""
    dist = root / "dist"
    dist.mkdir(parents=True)
    for name in ("superwiki-init", "skills.sh", "SKILL.md"):
        shutil.copy2(REPO_ROOT / name, dist / name)
    shutil.copytree(REPO_ROOT / "references", dist / "references")
    return dist


def clean_env(home: Path) -> dict:
    env = os.environ.copy()
    for key in ("CODEX_HOME", "OPENCODE_CONFIG_DIR"):
        env.pop(key, None)
    env["HOME"] = str(home)
    return env


def tree_snapshot(root: Path) -> dict:
    """Capture directories, files (bytes) and symlink targets below ``root``."""
    snapshot = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[rel] = ("link", os.readlink(path))
        elif path.is_dir():
            snapshot[rel] = ("dir",)
        else:
            snapshot[rel] = ("file", path.read_bytes())
    return snapshot


class InstallerTestCase(unittest.TestCase):
    def sandbox(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="superwiki-install-"))
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def run_script(self, script: Path, *args, cwd: Path, home: Path):
        return subprocess.run(
            [BASH, str(script), *[str(arg) for arg in args]],
            cwd=str(cwd),
            env=clean_env(home),
            capture_output=True,
            text=True,
        )

    def assert_link_to(self, link: Path, target: Path) -> None:
        self.assertTrue(link.is_symlink(), f"{link} is not a symlink")
        self.assertEqual(
            Path(os.path.realpath(link)),
            Path(os.path.realpath(target)),
            f"{link} resolves to {os.path.realpath(link)}, expected {os.path.realpath(target)}",
        )


class ProjectInitializerTests(InstallerTestCase):
    def test_selected_runtime_links_shared_knowledge_store(self):
        root = self.sandbox()
        project = root / "project"
        project.mkdir()

        proc = self.run_script(
            INIT_SCRIPT, "--claude", project, cwd=root, home=root / "home"
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = project / ".wiki" / "skills"
        self.assertTrue(store.is_dir())
        self.assert_link_to(project / ".claude" / "skills", store)

        # The link exposes the same content as the single knowledge store.
        (store / "SKILL.md").write_text("# stored knowledge\n", encoding="utf-8")
        self.assertEqual(
            (project / ".claude" / "skills" / "SKILL.md").read_text(encoding="utf-8"),
            "# stored knowledge\n",
        )

        # No other runtime entry points are created for a selected runtime.
        for runtime_dir, _ in RUNTIME_LINKS:
            if runtime_dir == ".claude":
                continue
            self.assertFalse(
                (project / runtime_dir).exists(),
                f"{runtime_dir} should not exist after --claude",
            )
        self.assertFalse((project / ".codex").exists())

    def test_default_and_all_initialize_every_runtime(self):
        for flags in ((), ("--all",)):
            with self.subTest(flags=flags):
                root = self.sandbox()
                project = root / "project"
                project.mkdir()

                proc = self.run_script(
                    INIT_SCRIPT, *flags, project, cwd=root, home=root / "home"
                )

                self.assertEqual(proc.returncode, 0, proc.stderr)
                store = project / ".wiki" / "skills"
                self.assertTrue(store.is_dir())
                for _, link_path in RUNTIME_LINKS:
                    self.assert_link_to(project / link_path, store)

    def test_paths_with_spaces_stay_functional(self):
        root = self.sandbox()
        project = root / "project with spaces"
        project.mkdir()
        workdir = root / "work dir"
        workdir.mkdir()
        (root / "home").mkdir()

        proc = self.run_script(INIT_SCRIPT, project, cwd=workdir, home=root / "home")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = project / ".wiki" / "skills"
        for _, link_path in RUNTIME_LINKS:
            self.assert_link_to(project / link_path, store)

    def test_repeated_run_preserves_store_and_links(self):
        root = self.sandbox()
        project = root / "project"
        project.mkdir()

        first = self.run_script(INIT_SCRIPT, project, cwd=root, home=root / "home")
        self.assertEqual(first.returncode, 0, first.stderr)

        store = project / ".wiki" / "skills"
        marker = store / "keep.md"
        marker.write_text("do not delete\n", encoding="utf-8")

        second = self.run_script(INIT_SCRIPT, project, cwd=root, home=root / "home")
        self.assertEqual(second.returncode, 0, second.stderr)

        self.assertEqual(marker.read_text(encoding="utf-8"), "do not delete\n")
        for _, link_path in RUNTIME_LINKS:
            self.assert_link_to(project / link_path, store)

    def test_conflicting_file_and_wrong_symlink_not_overwritten(self):
        root = self.sandbox()
        project = root / "project"
        project.mkdir()
        outside = root / "outside-skills"
        outside.mkdir()

        # A real file where a link would go must be left untouched.
        (project / ".claude").mkdir()
        claude_skills = project / ".claude" / "skills"
        claude_skills.write_text("user owned\n", encoding="utf-8")

        # A symlink pointing somewhere else must not be repointed.
        (project / ".agents").mkdir()
        agents_skills = project / ".agents" / "skills"
        agents_skills.symlink_to(outside)

        proc = self.run_script(INIT_SCRIPT, project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(claude_skills.is_symlink())
        self.assertEqual(
            claude_skills.read_text(encoding="utf-8"),
            "user owned\n",
        )
        self.assertTrue(agents_skills.is_symlink())
        self.assertEqual(Path(os.path.realpath(agents_skills)), Path(os.path.realpath(outside)))

        # Unrelated runtime entries are still installed.
        store = project / ".wiki" / "skills"
        self.assert_link_to(project / ".opencode" / "skills", store)
        self.assert_link_to(project / ".cursor" / "skills", store)

    def test_stale_hook_option_is_rejected_before_any_write(self):
        for args in (("--hook",), ("--hook", "project"), ("project", "--hook")):
            with self.subTest(args=args):
                root = self.sandbox()
                project = root / "project"
                project.mkdir()
                resolved = tuple(project if arg == "project" else arg for arg in args)

                proc = self.run_script(
                    INIT_SCRIPT, *resolved, cwd=root, home=root / "home"
                )

                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(list(project.iterdir()), [])
                self.assertFalse((root / ".wiki").exists())
                self.assertFalse((project / ".codex").exists())


class UninitializedProjectSafetyTests(InstallerTestCase):
    """Zero-footprint invariant: nothing is written without explicit setup.

    ``superwiki-init`` is the only component allowed to create ``.wiki`` state,
    and only when invoked with an explicit target.  Rejected options, invalid
    arguments and aborted runs must leave an uninitialized project byte-for-byte
    identical: no ``.wiki/``, no ``.wiki/staging.md``, no runtime links.
    """

    def assert_zero_footprint(self, root: Path, project: Path) -> None:
        self.assertFalse(
            os.path.lexists(project / ".wiki"), f"{project / '.wiki'} must not exist"
        )
        self.assertFalse(
            os.path.lexists(project / ".wiki" / "staging.md"),
            "staging.md must never be created by the installer",
        )
        for runtime_dir, link_path in RUNTIME_LINKS:
            self.assertFalse(
                os.path.lexists(project / link_path),
                f"{link_path} must not be created",
            )
        self.assertFalse(os.path.lexists(project / ".agents"))
        self.assertFalse(os.path.lexists(project / ".opencode"))
        self.assertFalse(os.path.lexists(project / ".cursor"))
        self.assertFalse(os.path.lexists(project / ".codex"))
        self.assertEqual(list(root.rglob("staging.md")), [])
        self.assertEqual(list(root.rglob(".wiki")), [])

    def test_rejected_options_and_invalid_commands_leave_no_footprint(self):
        cases = (
            ("--hook",),
            ("--hook", "project"),
            ("project", "--hook"),
            ("--bogus", "project"),
            ("-x", "project"),
            ("--wiki", "project"),
            ("project", "other"),
        )
        for args in cases:
            with self.subTest(args=args):
                root = self.sandbox()
                project = root / "project"
                project.mkdir()
                other = root / "other"
                other.mkdir()
                home = root / "home"
                targets = {"project": project, "other": other}
                resolved = tuple(targets.get(arg, arg) for arg in args)

                proc = self.run_script(
                    INIT_SCRIPT, *resolved, cwd=root, home=home
                )

                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assert_zero_footprint(root, project)
                self.assertEqual(list(project.iterdir()), [])
                self.assertEqual(list(other.iterdir()), [])
                self.assertFalse(home.exists())

    def test_aborted_or_help_runs_create_nothing(self):
        root = self.sandbox()
        home = root / "home"
        home.mkdir()

        # A missing project path is never created and never initialized.
        missing = root / "not-a-project"
        proc = self.run_script(INIT_SCRIPT, missing, cwd=root, home=home)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(missing.exists())
        self.assertEqual(sorted(path.name for path in root.iterdir()), ["home"])
        self.assertEqual(list(home.iterdir()), [])

        # A project path that is a regular file stays untouched.
        file_project = root / "afile"
        file_project.write_bytes(b"keep\n")
        proc = self.run_script(INIT_SCRIPT, file_project, cwd=root, home=home)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(file_project.is_symlink())
        self.assertEqual(file_project.read_bytes(), b"keep\n")
        self.assertEqual(list(root.rglob(".wiki")), [])
        self.assertEqual(list(root.rglob("staging.md")), [])
        self.assertEqual(list(home.iterdir()), [])

        # Help exits successfully but performs no writes, even with a target.
        project = root / "project"
        project.mkdir()
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                proc = self.run_script(
                    INIT_SCRIPT, flag, project, cwd=root, home=home
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("用法", proc.stdout)
                self.assert_zero_footprint(root, project)
                self.assertEqual(list(project.iterdir()), [])
                self.assertEqual(list(home.iterdir()), [])

    def test_failed_run_preserves_existing_user_content_exactly(self):
        root = self.sandbox()
        project = root / "project"
        (project / "src").mkdir(parents=True)
        (project / "README.md").write_bytes(b"keep me\n")
        (project / "src" / "main.py").write_bytes(b"print('hi')\n")
        claude_dir = project / ".claude"
        claude_dir.mkdir()
        settings = claude_dir / "settings.json"
        settings.write_bytes(b'{"theme": "dark"}\n')
        before = tree_snapshot(project)

        for args in (("--hook", project), ("--bogus", project), ("project", "extra")):
            with self.subTest(args=args):
                proc = self.run_script(
                    INIT_SCRIPT, *args, cwd=root, home=root / "home"
                )
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(tree_snapshot(project), before)
                self.assertEqual(
                    list(project.rglob(".wiki")), [], ".wiki must not appear"
                )
                self.assertEqual(list(project.rglob("staging.md")), [])

    def test_no_target_run_only_touches_the_resolved_cwd(self):
        root = self.sandbox()
        called_from = root / "cwd-project"
        called_from.mkdir()
        uninitialized_sibling = root / "sibling-project"
        uninitialized_sibling.mkdir()
        home = root / "home"
        home.mkdir()

        proc = self.run_script(INIT_SCRIPT, cwd=called_from, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = called_from / ".wiki" / "skills"
        self.assertTrue(store.is_dir())
        for _, link_path in RUNTIME_LINKS:
            self.assert_link_to(called_from / link_path, store)

        # The only footprint is under the explicit cwd; unrelated projects,
        # HOME and the sandbox root stay untouched, and staging is never made.
        self.assertEqual(list(uninitialized_sibling.iterdir()), [])
        self.assertFalse(os.path.lexists(uninitialized_sibling / ".wiki"))
        self.assertEqual(list(home.iterdir()), [])
        self.assertEqual(
            [path for path in root.rglob(".wiki") if path != called_from / ".wiki"],
            [],
        )
        self.assertEqual(list(root.rglob("staging.md")), [])
        self.assertFalse(os.path.lexists(root / ".agents"))
        self.assertFalse(os.path.lexists(root / ".opencode"))
        self.assertFalse(os.path.lexists(root / ".cursor"))


    def test_docs_forbid_wiki_and_staging_on_uninitialized_projects(self):
        """The written protocol must match the enforced zero-footprint rule."""
        for name in (
            "SKILL.md",
            os.path.join("references", "writing.md"),
            os.path.join("references", "initialization.md"),
        ):
            with self.subTest(doc=name):
                text = (REPO_ROOT / name).read_text(encoding="utf-8")
                self.assertRegex(
                    text,
                    r"(严禁|不得|禁止|不要)[^。\n]{0,40}staging",
                    f"{name} must forbid staging writes on uninitialized projects",
                )
                self.assertRegex(
                    text,
                    r"(严禁|不得|禁止|不要)[^。\n]{0,40}`\.wiki/` 目录",
                    f"{name} must forbid creating the .wiki/ directory",
                )


class GlobalInstallerTests(InstallerTestCase):
    def test_global_install_creates_only_superwiki_skill_link(self):
        root = self.sandbox()
        # Use spaces in the install source to exercise quoting.
        dist = make_dist(root / "install dir with spaces")
        home = root / "home"
        home.mkdir()

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        for skills_dir in GLOBAL_SKILL_DIRS:
            installed = home / skills_dir
            superwiki_link = installed / "superwiki"
            self.assert_link_to(superwiki_link, dist)
            # Installed links expose the real entrypoint and role docs.
            self.assertTrue((superwiki_link / "SKILL.md").is_file())
            for role in ("wiki-auditor.md", "initializer.md"):
                self.assertTrue(
                    (superwiki_link / "references" / "roles" / role).is_file()
                )

            # Fresh install dirs contain exactly this one skill: no siblings.
            self.assertEqual(
                sorted(path.name for path in installed.iterdir()), ["superwiki"]
            )

        # Runtime-specific skill dirs are not created at all: the installer
        # only targets the agent-compatible dir.
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            self.assertFalse(
                os.path.lexists(home / skills_dir),
                f"{skills_dir} must not be created by skills.sh",
            )

        # Installation never registers helper agents or creates agent dirs.
        for agents_dir in (
            home / ".codex" / "agents",
            home / ".config" / "opencode" / "agents",
            home / ".claude" / "agents",
            home / ".cursor" / "agents",
        ):
            self.assertFalse(agents_dir.exists())

    def test_global_install_preserves_preexisting_unrelated_skill_entries(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"

        # A foreign skill symlink is never repointed.
        foreign_librarian = root / "foreign" / "librarian"
        foreign_librarian.mkdir(parents=True)
        (foreign_librarian / "SKILL.md").write_text(
            "user owned librarian\n", encoding="utf-8"
        )
        claude_skills = home / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        librarian_link = claude_skills / "librarian"
        librarian_link.symlink_to(foreign_librarian)

        # An existing unrelated skill directory is left untouched.
        explorer_dir = home / ".config" / "opencode" / "skills" / "explorer"
        explorer_dir.mkdir(parents=True)
        explorer_marker = explorer_dir / "marker.txt"
        explorer_marker.write_text("user owned explorer\n", encoding="utf-8")

        # An existing unrelated skill file is left untouched.
        agents_skills = home / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        explorer_file = agents_skills / "explorer"
        explorer_bytes = b"user owned explorer file\n"
        explorer_file.write_bytes(explorer_bytes)

        # A dangling unrelated skill link also stays in place.
        dangling = home / ".cursor" / "skills" / "librarian"
        dangling.parent.mkdir(parents=True)
        dangling.symlink_to(root / "missing-librarian-target")

        # The Codex global dir holds a foreign entry too; it must never gain
        # this skill and must stay byte-for-byte identical.
        codex_skills = home / ".codex" / "skills"
        codex_skills.mkdir(parents=True)
        codex_foreign = codex_skills / "other-skill"
        codex_foreign_bytes = b"user owned codex skill\n"
        codex_foreign.write_bytes(codex_foreign_bytes)

        untouched = {
            skills_dir: tree_snapshot(home / skills_dir)
            for skills_dir in OTHER_GLOBAL_SKILL_DIRS
        }
        catalog_before = sorted(path.name for path in agents_skills.iterdir())

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        self.assertTrue(librarian_link.is_symlink())
        self.assertEqual(os.readlink(librarian_link), str(foreign_librarian))
        self.assertEqual(
            (librarian_link / "SKILL.md").read_text(encoding="utf-8"),
            "user owned librarian\n",
        )
        self.assertEqual(
            explorer_marker.read_text(encoding="utf-8"), "user owned explorer\n"
        )
        self.assertFalse(explorer_file.is_symlink())
        self.assertEqual(explorer_file.read_bytes(), explorer_bytes)
        self.assertTrue(dangling.is_symlink())
        self.assertFalse(dangling.exists())
        self.assertEqual(os.readlink(dangling), str(root / "missing-librarian-target"))

        self.assertEqual(codex_foreign.read_bytes(), codex_foreign_bytes)

        # Only the agent-compatible scope receives the link. Every other
        # runtime skill dir stays byte-for-byte identical and never gains a
        # SuperWiki entry.
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            installed = home / skills_dir
            self.assertEqual(
                tree_snapshot(installed),
                untouched[skills_dir],
                f"{skills_dir} must not be modified by skills.sh",
            )
            self.assertFalse(
                os.path.lexists(installed / "superwiki"),
                f"{skills_dir} must not receive a superwiki link",
            )

        # The install target keeps its foreign entry and gains exactly one link.
        self.assertEqual(
            sorted(path.name for path in agents_skills.iterdir()),
            sorted(catalog_before + ["superwiki"]),
        )
        self.assert_link_to(agents_skills / "superwiki", dist)

    def test_global_install_preserves_unrelated_settings_and_creates_no_hooks(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"
        hook_config = home / ".codex" / "hooks.json"
        codex_config = home / ".codex" / "config.toml"
        claude_settings = home / ".claude" / "settings.json"
        hook_config.parent.mkdir(parents=True)
        claude_settings.parent.mkdir(parents=True)

        hook_bytes = b'{"hooks": {"UserPromptSubmit": ["user-owned.sh"]}}\n'
        config_bytes = b'model = "user-choice"\n'
        settings_bytes = b'{"theme": "dark"}\n'
        hook_config.write_bytes(hook_bytes)
        codex_config.write_bytes(config_bytes)
        claude_settings.write_bytes(settings_bytes)

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(hook_config.read_bytes(), hook_bytes)
        self.assertEqual(codex_config.read_bytes(), config_bytes)
        self.assertEqual(claude_settings.read_bytes(), settings_bytes)

        # Skill installation alone never adds hook scripts or plugin config.
        self.assertFalse((home / ".codex" / "hooks").exists())
        self.assertFalse((home / ".codex" / "hooks.global.json").exists())
        self.assertEqual(
            list(home.rglob("superwiki-memory-hook.py")),
            [],
        )
        self.assertEqual(
            [path for path in home.rglob("hooks.json")],
            [hook_config],
        )

    def test_global_install_preserves_preexisting_agent_entries(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"

        # A stale distribution may still ship the retired helper definitions.
        legacy_agents = dist / "agents"
        legacy_agents.mkdir()
        legacy_bytes = {
            "memory-librarian.toml": b'name = "retired-memory-librarian"\n',
            "superwiki-initializer.toml": b'name = "retired-superwiki-initializer"\n',
            "superwiki-initializer.md": (
                b"---\nname: retired-superwiki-initializer\n---\n"
            ),
        }
        for name, content in legacy_bytes.items():
            (legacy_agents / name).write_bytes(content)

        # A user-owned foreign agent definition and a retired SuperWiki-named
        # link in an existing agents dir must survive installation untouched.
        codex_agents = home / ".codex" / "agents"
        codex_agents.mkdir(parents=True)
        foreign_agent = codex_agents / "memory-librarian.toml"
        foreign_bytes = b'name = "user-memory-librarian"\n'
        foreign_agent.write_bytes(foreign_bytes)
        # User-owned librarian/explorer agent configs captured before install
        # must remain byte-identical; the installer has no agent step.
        librarian_agent = codex_agents / "librarian.toml"
        librarian_agent_bytes = b'name = "user-librarian"\nmodel = "user-choice"\n'
        librarian_agent.write_bytes(librarian_agent_bytes)
        explorer_agent = codex_agents / "explorer.toml"
        explorer_agent_bytes = b'name = "user-explorer"\neffort = "user-choice"\n'
        explorer_agent.write_bytes(explorer_agent_bytes)
        elsewhere = root / "elsewhere.toml"
        elsewhere.write_bytes(b'name = "old-superwiki"\n')
        retired_link = codex_agents / "superwiki-initializer.toml"
        retired_link.symlink_to(elsewhere)
        retired_target = os.readlink(retired_link)

        # A real file where a helper link used to go is likewise untouched.
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        claude_agent = claude_agents / "superwiki-initializer.md"
        claude_bytes = b"---\nname: user-owned\n---\n"
        claude_agent.write_bytes(claude_bytes)

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        # The stale definitions in the distribution are never consumed.
        for name, content in legacy_bytes.items():
            self.assertEqual((legacy_agents / name).read_bytes(), content)

        self.assertFalse(foreign_agent.is_symlink())
        self.assertEqual(foreign_agent.read_bytes(), foreign_bytes)
        self.assertFalse(librarian_agent.is_symlink())
        self.assertEqual(librarian_agent.read_bytes(), librarian_agent_bytes)
        self.assertFalse(explorer_agent.is_symlink())
        self.assertEqual(explorer_agent.read_bytes(), explorer_agent_bytes)
        self.assertTrue(retired_link.is_symlink())
        self.assertEqual(os.readlink(retired_link), retired_target)
        self.assertEqual(elsewhere.read_bytes(), b'name = "old-superwiki"\n')
        self.assertFalse(claude_agent.is_symlink())
        self.assertEqual(claude_agent.read_bytes(), claude_bytes)

        # Existing agent dirs gain no new entries; absent ones stay absent.
        self.assertEqual(
            sorted(path.name for path in codex_agents.iterdir()),
            [
                "explorer.toml",
                "librarian.toml",
                "memory-librarian.toml",
                "superwiki-initializer.toml",
            ],
        )
        self.assertEqual(
            sorted(path.name for path in claude_agents.iterdir()),
            ["superwiki-initializer.md"],
        )
        for absent_agents_dir in (
            home / ".config" / "opencode" / "agents",
            home / ".cursor" / "agents",
        ):
            self.assertFalse(absent_agents_dir.exists())

        # The skill link is still installed, but only in the agent-compatible
        # global skill dir; other runtime skill dirs are not created.
        agents_skills = home / ".agents" / "skills"
        self.assert_link_to(agents_skills / "superwiki", dist)
        self.assertEqual(
            sorted(path.name for path in agents_skills.iterdir()), ["superwiki"]
        )
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            self.assertFalse(
                os.path.lexists(home / skills_dir),
                f"{skills_dir} must not be created by skills.sh",
            )


if __name__ == "__main__":
    unittest.main()
