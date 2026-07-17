"""Tests that exercise the inner tool functions created by register_* functions.

The register_* functions create inner async functions decorated with @agent.tool.
To cover those inner function bodies, we make agent.tool act as a pass-through
decorator, then call the registered function directly.
"""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a fake agent where .tool is a pass-through decorator."""
    agent = MagicMock()
    registered = {}

    def tool_decorator(fn):
        registered[fn.__name__] = fn
        return fn

    agent.tool = tool_decorator
    agent._registered = registered
    return agent


def _mock_context():
    return MagicMock()


# ===== browser_control.py register functions =====


class TestBrowserControlRegister:
    @pytest.mark.asyncio
    async def test_browser_initialize(self):
        from fid_coder.tools.browser.browser_control import register_initialize_browser

        agent = _make_agent()
        register_initialize_browser(agent)
        fn = agent._registered["browser_initialize"]
        with patch(
            "fid_coder.tools.browser.browser_control.initialize_browser",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_close(self):
        from fid_coder.tools.browser.browser_control import register_close_browser

        agent = _make_agent()
        register_close_browser(agent)
        fn = agent._registered["browser_close"]
        with patch(
            "fid_coder.tools.browser.browser_control.close_browser",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_status(self):
        from fid_coder.tools.browser.browser_control import register_get_browser_status

        agent = _make_agent()
        register_get_browser_status(agent)
        fn = agent._registered["browser_status"]
        with patch(
            "fid_coder.tools.browser.browser_control.get_browser_status",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_new_page(self):
        from fid_coder.tools.browser.browser_control import register_create_new_page

        agent = _make_agent()
        register_create_new_page(agent)
        fn = agent._registered["browser_new_page"]
        with patch(
            "fid_coder.tools.browser.browser_control.create_new_page",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_list_pages(self):
        from fid_coder.tools.browser.browser_control import register_list_pages

        agent = _make_agent()
        register_list_pages(agent)
        fn = agent._registered["browser_list_pages"]
        with patch(
            "fid_coder.tools.browser.browser_control.list_pages",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True


# ===== browser_navigation.py register functions =====


class TestBrowserNavigationRegister:
    @pytest.mark.asyncio
    async def test_browser_navigate(self):
        from fid_coder.tools.browser.browser_navigation import register_navigate_to_url

        agent = _make_agent()
        register_navigate_to_url(agent)
        fn = agent._registered["browser_navigate"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.navigate_to_url",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), url="http://x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_get_page_info(self):
        from fid_coder.tools.browser.browser_navigation import register_get_page_info

        agent = _make_agent()
        register_get_page_info(agent)
        fn = agent._registered["browser_get_page_info"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.get_page_info",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_go_back(self):
        from fid_coder.tools.browser.browser_navigation import register_browser_go_back

        agent = _make_agent()
        register_browser_go_back(agent)
        fn = agent._registered["browser_go_back"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.go_back",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_go_forward(self):
        from fid_coder.tools.browser.browser_navigation import (
            register_browser_go_forward,
        )

        agent = _make_agent()
        register_browser_go_forward(agent)
        fn = agent._registered["browser_go_forward"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.go_forward",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_reload(self):
        from fid_coder.tools.browser.browser_navigation import register_reload_page

        agent = _make_agent()
        register_reload_page(agent)
        fn = agent._registered["browser_reload"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.reload_page",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_browser_wait_for_load(self):
        from fid_coder.tools.browser.browser_navigation import (
            register_wait_for_load_state,
        )

        agent = _make_agent()
        register_wait_for_load_state(agent)
        fn = agent._registered["browser_wait_for_load"]
        with patch(
            "fid_coder.tools.browser.browser_navigation.wait_for_load_state",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True


# ===== browser_interactions.py register functions =====


class TestBrowserInteractionsRegister:
    @pytest.mark.asyncio
    async def test_click(self):
        from fid_coder.tools.browser.browser_interactions import register_click_element

        agent = _make_agent()
        register_click_element(agent)
        fn = agent._registered["browser_click"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.click_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_double_click(self):
        from fid_coder.tools.browser.browser_interactions import (
            register_double_click_element,
        )

        agent = _make_agent()
        register_double_click_element(agent)
        fn = agent._registered["browser_double_click"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.double_click_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_hover(self):
        from fid_coder.tools.browser.browser_interactions import register_hover_element

        agent = _make_agent()
        register_hover_element(agent)
        fn = agent._registered["browser_hover"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.hover_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_set_text(self):
        from fid_coder.tools.browser.browser_interactions import (
            register_set_element_text,
        )

        agent = _make_agent()
        register_set_element_text(agent)
        fn = agent._registered["browser_set_text"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.set_element_text",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x", text="hi")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_get_text(self):
        from fid_coder.tools.browser.browser_interactions import (
            register_get_element_text,
        )

        agent = _make_agent()
        register_get_element_text(agent)
        fn = agent._registered["browser_get_text"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.get_element_text",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_get_value(self):
        from fid_coder.tools.browser.browser_interactions import (
            register_get_element_value,
        )

        agent = _make_agent()
        register_get_element_value(agent)
        fn = agent._registered["browser_get_value"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.get_element_value",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_select_option(self):
        from fid_coder.tools.browser.browser_interactions import register_select_option

        agent = _make_agent()
        register_select_option(agent)
        fn = agent._registered["browser_select_option"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.select_option",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x", value="a")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_check(self):
        from fid_coder.tools.browser.browser_interactions import register_browser_check

        agent = _make_agent()
        register_browser_check(agent)
        fn = agent._registered["browser_check"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.check_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_uncheck(self):
        from fid_coder.tools.browser.browser_interactions import (
            register_browser_uncheck,
        )

        agent = _make_agent()
        register_browser_uncheck(agent)
        fn = agent._registered["browser_uncheck"]
        with patch(
            "fid_coder.tools.browser.browser_interactions.uncheck_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True


# ===== browser_locators.py register functions =====


class TestBrowserLocatorsRegister:
    @pytest.mark.asyncio
    async def test_find_by_role(self):
        from fid_coder.tools.browser.browser_locators import register_find_by_role

        agent = _make_agent()
        register_find_by_role(agent)
        fn = agent._registered["browser_find_by_role"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_by_role",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), role="button")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_by_text(self):
        from fid_coder.tools.browser.browser_locators import register_find_by_text

        agent = _make_agent()
        register_find_by_text(agent)
        fn = agent._registered["browser_find_by_text"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_by_text",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), text="hi")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_by_label(self):
        from fid_coder.tools.browser.browser_locators import register_find_by_label

        agent = _make_agent()
        register_find_by_label(agent)
        fn = agent._registered["browser_find_by_label"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_by_label",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), text="email")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_by_placeholder(self):
        from fid_coder.tools.browser.browser_locators import (
            register_find_by_placeholder,
        )

        agent = _make_agent()
        register_find_by_placeholder(agent)
        fn = agent._registered["browser_find_by_placeholder"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_by_placeholder",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), text="search")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_by_test_id(self):
        from fid_coder.tools.browser.browser_locators import register_find_by_test_id

        agent = _make_agent()
        register_find_by_test_id(agent)
        fn = agent._registered["browser_find_by_test_id"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_by_test_id",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), test_id="btn")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_xpath_query(self):
        from fid_coder.tools.browser.browser_locators import register_run_xpath_query

        agent = _make_agent()
        register_run_xpath_query(agent)
        fn = agent._registered["browser_xpath_query"]
        with patch(
            "fid_coder.tools.browser.browser_locators.run_xpath_query",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), xpath="//div")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_buttons(self):
        from fid_coder.tools.browser.browser_locators import register_find_buttons

        agent = _make_agent()
        register_find_buttons(agent)
        fn = agent._registered["browser_find_buttons"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_buttons",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_find_links(self):
        from fid_coder.tools.browser.browser_locators import register_find_links

        agent = _make_agent()
        register_find_links(agent)
        fn = agent._registered["browser_find_links"]
        with patch(
            "fid_coder.tools.browser.browser_locators.find_links",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True


# ===== browser_scripts.py register functions =====


class TestBrowserScriptsRegister:
    @pytest.mark.asyncio
    async def test_execute_js(self):
        from fid_coder.tools.browser.browser_scripts import register_execute_javascript

        agent = _make_agent()
        register_execute_javascript(agent)
        fn = agent._registered["browser_execute_js"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.execute_javascript",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), script="1+1")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_scroll(self):
        from fid_coder.tools.browser.browser_scripts import register_scroll_page

        agent = _make_agent()
        register_scroll_page(agent)
        fn = agent._registered["browser_scroll"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.scroll_page",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_scroll_to_element(self):
        from fid_coder.tools.browser.browser_scripts import register_scroll_to_element

        agent = _make_agent()
        register_scroll_to_element(agent)
        fn = agent._registered["browser_scroll_to_element"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.scroll_to_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_set_viewport(self):
        from fid_coder.tools.browser.browser_scripts import register_set_viewport_size

        agent = _make_agent()
        register_set_viewport_size(agent)
        fn = agent._registered["browser_set_viewport"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.set_viewport_size",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), width=800, height=600)
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_wait_for_element(self):
        from fid_coder.tools.browser.browser_scripts import register_wait_for_element

        agent = _make_agent()
        register_wait_for_element(agent)
        fn = agent._registered["browser_wait_for_element"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.wait_for_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_highlight_element(self):
        from fid_coder.tools.browser.browser_scripts import (
            register_browser_highlight_element,
        )

        agent = _make_agent()
        register_browser_highlight_element(agent)
        fn = agent._registered["browser_highlight_element"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.highlight_element",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), selector="#x")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_clear_highlights(self):
        from fid_coder.tools.browser.browser_scripts import (
            register_browser_clear_highlights,
        )

        agent = _make_agent()
        register_browser_clear_highlights(agent)
        fn = agent._registered["browser_clear_highlights"]
        with patch(
            "fid_coder.tools.browser.browser_scripts.clear_highlights",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True


# ===== browser_screenshot.py register functions =====


class TestBrowserScreenshotRegister:
    @pytest.mark.asyncio
    async def test_screenshot_analyze(self):
        from fid_coder.tools.browser.browser_screenshot import (
            register_take_screenshot_and_analyze,
        )

        agent = _make_agent()
        register_take_screenshot_and_analyze(agent)
        fn = agent._registered["browser_screenshot_analyze"]
        with patch(
            "fid_coder.tools.browser.browser_screenshot.take_screenshot",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True


# ===== browser_workflows.py register functions =====


class TestBrowserWorkflowsRegister:
    @pytest.mark.asyncio
    async def test_save_workflow(self):
        from fid_coder.tools.browser.browser_workflows import register_save_workflow

        agent = _make_agent()
        register_save_workflow(agent)
        fn = agent._registered["browser_save_workflow"]
        with patch(
            "fid_coder.tools.browser.browser_workflows.save_workflow",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), name="test", content="# Test")
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        from fid_coder.tools.browser.browser_workflows import register_list_workflows

        agent = _make_agent()
        register_list_workflows(agent)
        fn = agent._registered["browser_list_workflows"]
        with patch(
            "fid_coder.tools.browser.browser_workflows.list_workflows",
            return_value={"success": True},
        ):
            r = await fn(_mock_context())
            assert r["success"] is True

    @pytest.mark.asyncio
    async def test_read_workflow(self):
        from fid_coder.tools.browser.browser_workflows import register_read_workflow

        agent = _make_agent()
        register_read_workflow(agent)
        fn = agent._registered["browser_read_workflow"]
        with patch(
            "fid_coder.tools.browser.browser_workflows.read_workflow",
            return_value={"success": True},
        ):
            r = await fn(_mock_context(), name="test")
            assert r["success"] is True
