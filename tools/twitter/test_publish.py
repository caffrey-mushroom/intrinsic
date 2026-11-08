#!/usr/bin/env python3
"""Archive semantics: a newer revision replaces the same date+edition; a new date does not delete the old one."""
import json, tempfile, unittest
from pathlib import Path

from publish import publish

HOME = """<!doctype html><html><body><main>
  <section class="sec"><h2 class="sec-t">Notes</h2></section>
</main></body></html>
"""

V2 = """<h1>ignore</h1>
<h2>Executive Summary</h2>
<h3>核心判断</h3>
<p>V2TEXT 合同可执行性</p>
<h2>Highlights</h2>
<h3>1. 第一条</h3>
<p>固定窗口：2026-11-07 21:30:00 至 2026-11-08 21:30:00 北京时间</p>
<div id="post-100"><h4>晚报要点</h4>
<p><a href="https://x.com/example/status/100">原帖</a></p>
<p><a href="javascript:alert(1)">丢弃</a><script>alert(1)</script>正文</p>
<img src="https://pbs.twimg.com/media/a.jpg" alt="图" onerror="alert(1)">
<img src="javascript:alert(1)" alt="no">
</div>
"""

V1 = V2.replace("V2TEXT", "V1TEXT")
N9 = """<h2>Executive Summary</h2><h3>明天</h3><p>N9TEXT</p>
<div id="post-200"><h4>早报要点</h4><p>固定窗口：2026-11-08 21:30:00 至 2026-11-09 09:30:00 北京时间</p></div>
"""


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "index.html").write_text(HOME, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def page(self, slug):
        return (self.repo / "twitter" / slug / "index.html").read_text(encoding="utf-8")

    def test_nov8_v2_remains_after_nov9_and_rejects_late_v1(self):
        added = publish(self.repo, V2, "2026-11-08", "pm", "2026-11-08T14:19:37Z")
        self.assertEqual(added["status"], "add")
        self.assertIn("V2TEXT", self.page("2026-11-08-pm"))
        self.assertNotIn("V1TEXT", self.page("2026-11-08-pm"))
        self.assertIn('rel="noopener noreferrer"', self.page("2026-11-08-pm"))
        self.assertNotIn("alert(1)", self.page("2026-11-08-pm"))
        self.assertNotIn("javascript:", self.page("2026-11-08-pm"))
        self.assertNotIn("onerror", self.page("2026-11-08-pm"))
        self.assertIn("https://pbs.twimg.com/media/a.jpg", self.page("2026-11-08-pm"))
        self.assertIn("font-weight:600", self.page("2026-11-08-pm"))
        self.assertIn("<h3>", self.page("2026-11-08-pm"))
        self.assertIn("<h4>", self.page("2026-11-08-pm"))

        late = publish(self.repo, V1, "2026-11-08", "pm", "2026-11-08T13:41:13Z")
        self.assertEqual(late["status"], "skip")
        self.assertIn("V2TEXT", self.page("2026-11-08-pm"))
        self.assertNotIn("V1TEXT", self.page("2026-11-08-pm"))
        editions = json.loads((self.repo / "twitter" / "editions.json").read_text())
        self.assertEqual([item["slug"] for item in editions], ["2026-11-08-pm"])

        again = publish(self.repo, V2, "2026-11-08", "pm", "2026-11-08T14:19:37Z")
        self.assertEqual(again["status"], "unchanged")

        nxt = publish(self.repo, N9, "2026-11-09", "am", "2026-11-09T01:05:00Z")
        self.assertEqual(nxt["status"], "add")
        self.assertIn("N9TEXT", self.page("2026-11-09-am"))
        self.assertIn("V2TEXT", self.page("2026-11-08-pm"))
        editions = json.loads((self.repo / "twitter" / "editions.json").read_text())
        self.assertEqual([item["slug"] for item in editions], ["2026-11-09-am", "2026-11-08-pm"])
        index = (self.repo / "twitter" / "index.html").read_text(encoding="utf-8")
        self.assertLess(index.index("2026-11-09-am"), index.index("2026-11-08-pm"))
        home = (self.repo / "index.html").read_text(encoding="utf-8")
        self.assertIn(">twitter</div>", home)
        self.assertIn("最新：2026.11.09 早报", home)
        self.assertIn("2 期", home)
        self.assertLess(home.index('id="twitter"'), home.index("</main>"))
        self.assertIn("Notes", home)

    def test_same_day_morning_and_evening_are_distinct(self):
        publish(self.repo, V2, "2026-11-08", "am", "2026-11-08T21:30:00+08:00")
        publish(self.repo, V2.replace("V2TEXT", "PMTEXT"), "2026-11-08", "pm", "2026-11-08T14:19:37Z")
        editions = json.loads((self.repo / "twitter" / "editions.json").read_text())
        self.assertEqual([item["slug"] for item in editions], ["2026-11-08-pm", "2026-11-08-am"])
        self.assertIn("PMTEXT", self.page("2026-11-08-pm"))
        self.assertIn("V2TEXT", self.page("2026-11-08-am"))


if __name__ == "__main__":
    unittest.main()
