import subprocess
import sys
import unittest
from pathlib import Path

from core.agent_orchestrator import AgentOrchestrator
from core.agents.meeting_agent import CONTRADICTED, UNVERIFIED, VERIFIED, MeetingAgent, TranscriptSegment
from core.agents.job_agent import APPROVED, REVIEW_REQUIRED, JobAgent, JobPosting, JobSource
from core.workspace_manager import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_desktop_alias_resolves_to_user_desktop(self):
        wm = WorkspaceManager()
        desktop = wm.resolve_user_path("desktop")
        self.assertEqual(desktop, Path.home() / "Desktop")

    def test_absolute_path_is_preserved(self):
        wm = WorkspaceManager()
        target = Path("C:/Projects/Atlas")
        self.assertEqual(wm.resolve_user_path(str(target)), target)

    def test_project_path_tracks_last_created_path(self):
        wm = WorkspaceManager()
        temp_root = Path.home() / "Desktop" / "AtlasWorkspaceTest"
        if temp_root.exists():
            import shutil
            shutil.rmtree(temp_root, ignore_errors=True)

        created = wm.create_directory("desktop", "AtlasWorkspaceTest")
        self.assertTrue(created.exists())
        self.assertEqual(wm.last_created_path(), created)

    def test_agent_orchestrator_runs_tasks(self):
        orchestrator = AgentOrchestrator()
        task = orchestrator.create_task("coding", "Build a simple ML demo")
        result = orchestrator.run_task(task)
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(result["agent"], "coding")
        self.assertTrue(Path(result["target_dir"]).exists())

    def test_coding_agent_creates_python_scaffold_and_venv(self):
        agent = AgentOrchestrator().agents["coding"]
        path = agent.create_project("Sample app", "desktop")
        self.assertTrue((path / "main.py").exists())
        self.assertTrue((path / ".venv").exists())

        venv_python = path / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        result = subprocess.run([str(venv_python), str(path / "main.py")], capture_output=True, text=True, cwd=path)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        requirements_result = subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(path / "requirements.txt")], capture_output=True, text=True, cwd=path)
        self.assertEqual(requirements_result.returncode, 0, msg=requirements_result.stderr or requirements_result.stdout)

    def test_orchestrator_coding_run_validates_project(self):
        orchestrator = AgentOrchestrator()
        task = orchestrator.create_task("coding", "Build a demo app")
        result = orchestrator.run_task(task)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(Path(result["target_dir"]).exists())

    def test_coding_agent_returns_structured_final_report(self):
        agent = AgentOrchestrator().agents["coding"]
        result = agent.plan_project("Final report app")
        report = result["final_report"]
        self.assertEqual(
            set(report),
            {"Project Name", "Location", "Dependencies", "Test Results", "How to Run"},
        )
        self.assertEqual(report["Project Name"], "Final_report_app")
        self.assertEqual(report["Dependencies"], [])
        self.assertEqual(report["Test Results"]["status"], "SUCCESS")
        self.assertIn("main.py", report["How to Run"])

    def test_meeting_agent_processes_transcript_in_background(self):
        agent = MeetingAgent()
        try:
            future = agent.process_transcript_background(
                "The topic is deployment. The team will ship Friday."
            )
            result = future.result(timeout=5)
            self.assertEqual(len(result.transcript), 1)
            self.assertTrue(result.topics)
            self.assertTrue(result.claims)
        finally:
            agent.close()

    def test_meeting_agent_preserves_transcript_segments(self):
        agent = MeetingAgent()
        try:
            segments = [TranscriptSegment("The topic is reliability.", "Alex", 1.0, 3.0)]
            result = agent.process_transcript(segments)
            self.assertEqual(result.transcript, segments)
            self.assertEqual(result.transcript[0].speaker, "Alex")
        finally:
            agent.close()

    def test_meeting_agent_extracts_decisions_actions_and_verifies_claims(self):
        agent = MeetingAgent()
        try:
            transcript = [
                TranscriptSegment("Topic: deployment", "Alex"),
                TranscriptSegment("Decision: deploy the release on Friday.", "Alex"),
                TranscriptSegment("Action item: Jordan will publish release notes by Friday.", "Jordan"),
                TranscriptSegment("The staging test is green.", "Sam"),
                TranscriptSegment("The rollout is approved.", "Alex"),
                TranscriptSegment("The backup is complete.", "Sam"),
            ]
            analysis = agent.process_transcript(
                transcript,
                evidence={
                    "The staging test is green.": "Test report supports this claim.",
                    "The rollout is approved.": "Review record contradicts this claim.",
                },
            )

            self.assertEqual([item.text for item in analysis.decisions], ["Decision: deploy the release on Friday."])
            self.assertEqual(len(analysis.action_items), 1)
            self.assertEqual(analysis.action_items[0].owner, "Jordan")
            self.assertEqual(analysis.action_items[0].deadline, "Friday")
            statuses = {item.claim: item.status for item in analysis.evidence}
            self.assertEqual(statuses["The staging test is green."], VERIFIED)
            self.assertEqual(statuses["The rollout is approved."], CONTRADICTED)
            self.assertEqual(statuses["The backup is complete."], UNVERIFIED)
        finally:
            agent.close()

    def test_meeting_final_document_contains_only_extracted_facts(self):
        agent = MeetingAgent()
        try:
            analysis = agent.process_transcript(
                "Topic: reliability\nDecision: keep the maintenance window.\nAction item: Alex will update the runbook."
            )
            document = analysis.final_document
            self.assertEqual(document["topics"], ["Topic: reliability"])
            self.assertEqual(document["decisions"], ["Decision: keep the maintenance window."])
            self.assertEqual(document["action_items"][0]["owner"], "Alex")
            self.assertEqual(document["action_items"][0]["deadline"], None)
            self.assertEqual(
                document["claims"],
                [{"text": "Action item: Alex will update the runbook.", "status": "UNVERIFIED", "evidence": None}],
            )
            self.assertNotIn("summary", document)
            self.assertNotIn("attendees", document)
        finally:
            agent.close()

    def test_job_sources_deduplicate_postings(self):
        class Source(JobSource):
            name = "test"

            def fetch_jobs(self, query):
                return [
                    JobPosting("Python Engineer", "Atlas", "Remote", url="HTTPS://jobs.test/1/"),
                    JobPosting("Python Engineer", "Atlas", "Remote", url="https://jobs.test/1"),
                ]

        agent = JobAgent()
        agent.register_source(Source())
        jobs = agent.discover_jobs("python")
        self.assertEqual(len(jobs), 1)

    def test_job_parsing_and_explainable_matching(self):
        agent = JobAgent()
        posting = JobPosting(
            "Data Engineer",
            "Atlas",
            description="Required: Python, SQL, AWS. Preferred: Docker.",
        )
        profile = agent.parse_job_description(posting)
        resume = agent.parse_resume("Python and SQL engineer with Excel experience.", "Taylor")
        result = agent.match(profile, resume)
        self.assertEqual(result.score, 66.67)
        self.assertEqual(result.alignments, ["python", "sql"])
        self.assertEqual(result.gaps, ["aws"])

    def test_matched_job_requires_explicit_human_approval(self):
        agent = JobAgent()
        posting = JobPosting("Python Engineer", "Atlas", url="https://jobs.test/2")
        match = agent.match(
            agent.parse_job_description(JobPosting("Python Engineer", "Atlas", description="Required: Python")),
            agent.parse_resume("Python developer"),
        )
        tracked = agent.queue_for_review(posting, match)
        self.assertEqual(tracked.state, REVIEW_REQUIRED)
        self.assertEqual(len(agent.review_queue()), 1)
        self.assertEqual(agent.approve_job(posting).state, APPROVED)
        self.assertEqual(agent.review_queue(), [])

    def test_coding_agent_can_fix_a_failing_project(self):
        agent = AgentOrchestrator().agents["coding"]
        target = agent.create_project("Broken app", "desktop")

        broken_main = target / "main.py"
        broken_main.write_text("print('hello'\n", encoding="utf-8")

        fixed = agent.fix_project(target)
        self.assertTrue(fixed)
        self.assertTrue(broken_main.exists())

        venv_python = target / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        result = subprocess.run([str(venv_python), str(broken_main)], capture_output=True, text=True, cwd=target)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_coding_agent_repairs_traceback_based_errors(self):
        agent = AgentOrchestrator().agents["coding"]
        target = agent.create_project("Traceback app", "desktop")
        bad_main = target / "main.py"
        bad_main.write_text(
            "def main():\n    print(missing_name)\n\nif __name__ == '__main__':\n    main()\n",
            encoding="utf-8",
        )

        success = agent.fix_project(target)
        self.assertTrue(success)
        self.assertIn("Atlas project scaffold is ready.", bad_main.read_text(encoding="utf-8"))

    def test_coding_agent_preserves_custom_project_code_when_fixing(self):
        agent = AgentOrchestrator().agents["coding"]
        target = agent.create_project("Custom app", "desktop")
        custom_file = target / "custom_logic.py"
        custom_file.write_text(
            "def format_message(name: str) -> str:\n    return f'Hello {name}'\n",
            encoding="utf-8",
        )
        main_file = target / "main.py"
        main_file.write_text(
            "from custom_logic import format_message\n\nprint(format_message('Atlas'))\n",
            encoding="utf-8",
        )

        broken_main = target / "main.py"
        broken_main.write_text(
            "from custom_logic import format_message\n\nprint(format_message())\n",
            encoding="utf-8",
        )

        success = agent.fix_project(target)
        self.assertTrue(success)
        self.assertIn("def format_message", custom_file.read_text(encoding="utf-8"))
        self.assertIn("format_message('Atlas')", broken_main.read_text(encoding="utf-8"))

    def test_coding_agent_repairs_the_specific_failing_expression(self):
        agent = AgentOrchestrator().agents["coding"]
        target = agent.create_project("Line fix app", "desktop")
        main_file = target / "main.py"
        main_file.write_text(
            "from custom_logic import format_message\n\nvalue = format_message()\nprint(value)\n",
            encoding="utf-8",
        )

        custom_file = target / "custom_logic.py"
        custom_file.write_text(
            "def format_message(name: str) -> str:\n    return f'Hello {name}'\n",
            encoding="utf-8",
        )

        success = agent.fix_project(target)
        self.assertTrue(success)
        self.assertIn("format_message('Atlas')", main_file.read_text(encoding="utf-8"))

    def test_coding_agent_parses_traceback_filename_and_line(self):
        agent = AgentOrchestrator().agents["coding"]
        target = agent.create_project("Traceback parse app", "desktop")
        main_file = target / "main.py"
        main_file.write_text(
            "from custom_logic import format_message\n\nvalue = format_message()\nprint(value)\n",
            encoding="utf-8",
        )
        custom_file = target / "custom_logic.py"
        custom_file.write_text(
            "def format_message(name: str) -> str:\n    return f'Hello {name}'\n",
            encoding="utf-8",
        )

        failure = (
            'Traceback (most recent call last):\n'
            f'  File "{main_file}", line 3, in <module>\n'
            '    value = format_message()\n'
            "TypeError: format_message() missing 1 required positional argument: 'name'\n"
        )

        parsed_file, parsed_line = agent._parse_traceback_target(target, failure)
        self.assertEqual(parsed_file, main_file)
        self.assertEqual(parsed_line, 3)


if __name__ == "__main__":
    unittest.main()
