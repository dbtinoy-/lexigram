from lexigram.ui.core.base import raw, render_to_string
from lexigram.ui.molecules.modal import Modal
from lexigram.ui.organisms.slide_over import SlideOver


def test_modal_create_footer_from_title():
    m = Modal("Create User", trigger="Open", render_trigger=False)
    # With a raw HTML form present and no footer, we do not inject overlay buttons anymore
    m.add(raw('<form><input name="x"/></form>'))
    html = render_to_string(m)
    # Raw HTML forms won't be converted to a sticky Form component automatically, so no Cancel/Create is added by Modal
    assert "Cancel" not in html
    assert 'type="submit"' not in html

    # When the caller supplies footer actions, they should override defaults
    m.footer = [
        raw('<button class="cancel">Cancel</button>'),
        raw('<button class="create">Create</button>'),
    ]
    html2 = render_to_string(m)
    assert "Create" in html2
    assert "Cancel" in html2
    assert "gap-3" in html2


def test_modal_render_trigger_flag_and_accessibility():
    # When render_trigger=False we should not include the trigger button
    m = Modal("Test Modal", trigger="Open", render_trigger=False)
    html = render_to_string(m)
    assert "Open" not in html
    # Accessibility and escape handling attributes should be present on the overlay wrapper
    m2 = Modal("Test Modal", trigger="Open", render_trigger=True)
    html2 = render_to_string(m2)
    assert "Open" in html2
    assert "x-cloak" in html2
    assert "x-on:keydown.window.escape" in html2
    assert 'role="dialog"' in html2
    # Backdrop should close on click and overlay wrapper should use x-show
    assert "x-on:click" in html2
    assert "x-show" in html2
    # Modal sizing and layout
    assert "max-w-[33.333vw]" in html2
    assert "max-h-[66vh]" in html2
    assert "flex-1 overflow-y-auto" in html2
    assert "sticky bottom-0" in html2
    assert "items-center" in html2  # centered vertically

    # Slide over: ensure width change applies and footer sticky works when a form is present
    s3 = SlideOver("Edit Item", trigger="Edit", render_trigger=True)
    s3.add(raw('<form><input name="x"/></form>'))
    html3 = render_to_string(s3)
    assert "max-w-lg" in html3
    assert "overflow-y-auto" in html3
    # Default footer should be injected when a form is present
    assert "sticky bottom-0" in html3
    assert "Save" in html3
    assert 'type="submit"' in html3

    # When the caller supplies a footer action, it should override defaults
    s3.footer = [
        raw(
            "<button x-on:click=\"document.querySelector('form').requestSubmit()\">Save</button>",
        ),
    ]
    html4 = render_to_string(s3)
    assert "sticky bottom-0" in html4
    assert "Save" in html4
    assert "requestSubmit" in html4


def test_slide_over_trigger_logic_and_escape():
    # When render_trigger=False we should not include any trigger
    s = SlideOver("Edit Item", trigger="Edit", render_trigger=False)
    html = render_to_string(s)
    assert "text-primary hover:text-primary/80" not in html

    # When string trigger and render_trigger=True we should have action button
    s2 = SlideOver("Edit Item", trigger="Edit", render_trigger=True)
    html2 = render_to_string(s2)
    assert "text-primary hover:text-primary/80" in html2
    # Trigger should be right-aligned
    assert "justify-end" in html2
    # Ensure ESC handler and ARIA attributes are present
    assert "x-on:keydown.window.escape" in html2
    assert 'role="dialog"' in html2
    assert 'aria-modal="true"' in html2
