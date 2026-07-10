# Stylesheet organization

`site.css` is the compatibility entry point shared by the public website and
dashboard. Its sections are ordered as public marketing components, program and
event components, shared forms and messages, dashboard surfaces, then responsive
and CMS typography overrides.

Keep new selectors scoped to a public component or a `.dash-*` dashboard
component and place them beside the relevant existing section. Avoid appending
unrelated overrides, which increases specificity and makes regressions harder to
trace.
