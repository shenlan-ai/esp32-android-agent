// Presentation only: panels stay mounted; device and task decisions remain in their modules.
export function createConsoleView({ document, translate: t, location, history }) {
  const panels = [...document.querySelectorAll('[data-panel]')];
  const links = [...document.querySelectorAll('[data-console-view]')];
  const title = document.getElementById('workspace-title');
  const description = document.getElementById('workspace-description');
  const titles = { workspace:'workspace', devices:'connection', settings:'modelSettings' };
  const descriptions = { workspace:'workspaceHelp', devices:'connectionHelp', settings:'settingsHelp' };
  let view = 'workspace', model = null;

  function translated() {
    title.dataset.i18n = titles[view]; title.textContent = t(titles[view]);
    description.dataset.i18n = descriptions[view]; description.textContent = t(descriptions[view]);
    const summary = document.getElementById('model-summary');
    summary.textContent = model?.model?.trim() ? `${t('actor')}: ${model.model}` : t('configureModel');
  }
  function select(next, { focus = true, updateUrl = true } = {}) {
    if (!Object.hasOwn(titles, next)) next = 'workspace';
    view = next;
    document.querySelector('.app-shell').dataset.view = view;
    for (const panel of panels) {
      panel.hidden = panel.dataset.panel !== view;
      panel.classList.toggle('view-enter', !panel.hidden);
    }
    for (const link of links) {
      if (!link.closest('nav')) continue;
      if (link.dataset.consoleView === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    translated();
    if (updateUrl) {
      const url = new URL(location.href);
      if (view === 'workspace') url.searchParams.delete('view');
      else url.searchParams.set('view', view);
      history.replaceState(null, '', url);
    }
    if (focus) title.focus({ preventScroll:false });
  }
  for (const link of links) link.addEventListener('click', () => select(link.dataset.consoleView));
  select(new URL(location.href).searchParams.get('view') || 'workspace', {focus:false, updateUrl:false});
  return {
    translated,
    settings(prefs) { model = prefs.actor; translated(); },
    status(status) {
      document.getElementById('task-empty').hidden = !!status.agent?.id || (status.agent?.state ?? 'idle') !== 'idle';
    },
    select,
  };
}
