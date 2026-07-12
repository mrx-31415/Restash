(function (root, factory) {
  const logic = factory();
  if (typeof module === "object" && module.exports) module.exports = logic;
  if (root && root.PluginApi) logic.initialize(root.PluginApi);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ROUTE = "/restash/freshness";
  const LEGACY_ROUTE = "/plugin/restash/freshness";
  const INDEX_BATCH_SIZE = 1000;
  const PAGE_SIZES = [20, 40, 80, 120];
  const FILTER_OPERATORS = Object.freeze({ gte: "≥", gt: ">", eq: "=", lt: "<", lte: "≤" });
  const DEFAULTS = Object.freeze({ search: "", min: 95, op: "gte", page: 1, pageSize: 40 });

  function parseScore(value) {
    if (typeof value === "string") {
      if (!value.trim()) return null;
      value = Number(value);
    }
    if (typeof value !== "number" || !Number.isFinite(value) || !Number.isInteger(value)) return null;
    return value >= 1 && value <= 100 ? value : null;
  }

  function compareEntries(a, b) {
    if (a.score === null && b.score !== null) return 1;
    if (a.score !== null && b.score === null) return -1;
    if (a.score !== b.score) return b.score - a.score;
    const an = Number(a.id), bn = Number(b.id);
    if (Number.isSafeInteger(an) && Number.isSafeInteger(bn) && an !== bn) return an - bn;
    return String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
  }

  function matchesFilter(score, value, op) {
    if (score === null) return false;
    if (op === "gt") return score > value;
    if (op === "eq") return score === value;
    if (op === "lt") return score < value;
    if (op === "lte") return score <= value;
    return score >= value;
  }

  function filterEntries(entries, value, op) {
    return entries.filter((entry) => matchesFilter(entry.score, value, op));
  }

  function scoreCriterion(value, op) {
    if (op === "gt") return { field: "restash_score", value: [value], modifier: "GREATER_THAN" };
    if (op === "eq") return { field: "restash_score", value: [value], modifier: "EQUALS" };
    if (op === "lt") return { field: "restash_score", value: [value], modifier: "LESS_THAN" };
    if (op === "lte") return { field: "restash_score", value: [1, value], modifier: "BETWEEN" };
    return { field: "restash_score", value: [value, 100], modifier: "BETWEEN" };
  }

  function paginate(entries, page, pageSize) {
    return entries.slice((page - 1) * pageSize, page * pageSize);
  }

  function orderHydrated(ids, scenes) {
    const byId = new Map((scenes || []).map((scene) => [String(scene.id), scene]));
    return ids.map((id) => byId.get(String(id))).filter(Boolean);
  }

  function normalizeParams(input, defaults) {
    defaults = defaults || DEFAULTS;
    const params = input instanceof URLSearchParams ? input : new URLSearchParams(input || "");
    const minRaw = Number(params.get("min"));
    const pageRaw = Number(params.get("page"));
    const sizeRaw = Number(params.get("pageSize"));
    return {
      search: params.get("search") || defaults.search,
      min: Number.isInteger(minRaw) && minRaw >= 1 && minRaw <= 100 ? minRaw : defaults.min,
      op: Object.prototype.hasOwnProperty.call(FILTER_OPERATORS, params.get("op")) ? params.get("op") : defaults.op,
      page: Number.isInteger(pageRaw) && pageRaw > 0 ? pageRaw : defaults.page,
      pageSize: PAGE_SIZES.includes(sizeRaw) ? sizeRaw : defaults.pageSize,
    };
  }

  function toParams(state, defaults) {
    defaults = defaults || DEFAULTS;
    const params = new URLSearchParams();
    if (state.search) params.set("search", state.search);
    if (state.min !== defaults.min) params.set("min", String(state.min));
    if (state.op !== defaults.op) params.set("op", state.op);
    if (state.page !== defaults.page) params.set("page", String(state.page));
    if (state.pageSize !== defaults.pageSize) params.set("pageSize", String(state.pageSize));
    return params;
  }

  function initialize(Api) {
    if (globalThis.__restashFreshnessInitialized) return;
    globalThis.__restashFreshnessInitialized = true;

    const React = Api.React;
    const h = React.createElement;
    const Router = Api.libraries.ReactRouterDOM;
    const Bootstrap = Api.libraries.Bootstrap;
    const Apollo = Api.libraries.Apollo;
    const FA = Api.libraries.ReactFontAwesome;
    const icons = Api.libraries.FontAwesomeSolid;
    const INDEX_QUERY = Apollo.gql`query RestashFreshnessIndex($filter: FindFilterType, $sceneFilter: SceneFilterType) {
      findScenes(filter: $filter, scene_filter: $sceneFilter) { count scenes { id custom_fields } }
    }`;
    const CONFIG_QUERY = Apollo.gql`query RestashFreshnessConfiguration {
      configuration { plugins }
    }`;
    const markedScores = new Map();

    function FreshNavItem() {
      return h(Bootstrap.Nav.Link, { as: "div", eventKey: ROUTE, className: "restash-fresh-nav col-4 col-sm-3 col-md-2 col-lg-auto" },
        h(Router.NavLink, { exact: true, to: ROUTE, activeClassName: "active", className: "btn minimal p-4 p-xl-2 d-flex d-xl-inline-block flex-column justify-content-between align-items-center" },
          h(FA.FontAwesomeIcon, { icon: icons.faLeaf, className: "fa-icon nav-menu-icon d-block d-xl-inline mb-2 mb-xl-0" }),
          h("span", null, "Fresh")));
    }

    Api.patch.instead("MainNavBar.MenuItems", function (props, _context, original) {
      const children = React.Children.toArray(props.children);
      if (!children.some((child) => child && child.key === "restash-fresh-nav")) children.push(h(FreshNavItem, { key: "restash-fresh-nav" }));
      return original({ ...props, children });
    });

    Api.patch.after("SceneCard.Details", function (props, _context, result) {
      const score = markedScores.get(String(props.scene.id));
      if (score === undefined) return result;
      return h(React.Fragment, null, result, h("span", { className: "restash-freshness-badge", "data-restash-score": score }, `Fresh ${score}`));
    });

    function Status(props) {
      return h(Bootstrap.Alert, { variant: props.variant || "info", className: "restash-status" }, props.children);
    }

    function FreshnessPage() {
      const history = Router.useHistory();
      const location = Router.useLocation();
      const client = Apollo.useApolloClient();
      const [defaultMinimum, setDefaultMinimum] = React.useState(DEFAULTS.min);
      const defaults = React.useMemo(() => ({ ...DEFAULTS, min: defaultMinimum }), [defaultMinimum]);
      const explicitMinimum = React.useRef(new URLSearchParams(location.search).has("min"));
      const [state, setState] = React.useState(() => normalizeParams(location.search, defaults));
      const [searchInput, setSearchInput] = React.useState(state.search);
      const [index, setIndex] = React.useState([]);
      const [scenes, setScenes] = React.useState([]);
      const [selectedIds, setSelectedIds] = React.useState(() => new Set());
      const [zoomIndex, setZoomIndex] = React.useState(1);
      const [displayMode, setDisplayMode] = React.useState(0);
      const [phase, setPhase] = React.useState("loading");
      const [progress, setProgress] = React.useState({ loaded: 0, total: 0 });
      const [error, setError] = React.useState(null);
      const [taskRun, setTaskRun] = React.useState(null);
      const [indexRevision, setIndexRevision] = React.useState(0);
      const requestRef = React.useRef(0);
      const loadingComponents = Api.hooks.useLoadComponents([
        Api.loadableComponents.SceneCard,
        Api.loadableComponents.SceneList,
      ]);

      React.useEffect(() => {
        let cancelled = false;
        client.query({ query: CONFIG_QUERY, fetchPolicy: "network-only" }).then((response) => {
          if (cancelled) return;
          const plugins = response.data && response.data.configuration && response.data.configuration.plugins;
          const configured = Number(plugins && plugins.restash && plugins.restash.freshnessDefaultMinimum);
          if (Number.isInteger(configured) && configured >= 1 && configured <= 100) setDefaultMinimum(configured);
        }).catch(() => { /* The documented default remains usable if configuration cannot be read. */ });
        return () => { cancelled = true; };
      }, []);

      React.useEffect(() => {
        if (!taskRun || !taskRun.id || ["FINISHED", "FAILED", "CANCELLED"].includes(taskRun.status)) return;
        let cancelled = false;
        let timer;
        async function pollJob() {
          try {
            const response = await client.query({ query: Api.GQL.FindJobDocument, variables: { input: { id: taskRun.id } }, fetchPolicy: "network-only" });
            if (cancelled || !response.data.findJob) return;
            const job = response.data.findJob;
            setTaskRun((old) => old && old.id === taskRun.id ? { ...old, status: job.status, progress: job.progress, error: job.error } : old);
            if (job.status === "FINISHED") setIndexRevision((value) => value + 1);
            if (!["FINISHED", "FAILED", "CANCELLED"].includes(job.status)) timer = setTimeout(pollJob, 1000);
          } catch (caught) {
            if (!cancelled) setTaskRun((old) => old && old.id === taskRun.id ? { ...old, status: "FAILED", error: caught.message } : old);
          }
        }
        timer = setTimeout(pollJob, 500);
        return () => { cancelled = true; clearTimeout(timer); };
      }, [taskRun && taskRun.id]);

      React.useEffect(() => {
        if (!taskRun || !["FINISHED", "CANCELLED"].includes(taskRun.status)) return;
        const id = taskRun.id;
        const timer = setTimeout(() => setTaskRun((old) => old && old.id === id ? null : old), 4000);
        return () => clearTimeout(timer);
      }, [taskRun && taskRun.status]);

      React.useEffect(() => {
        const timer = setTimeout(() => setState((old) => old.search === searchInput ? old : { ...old, search: searchInput, page: 1 }), 350);
        return () => clearTimeout(timer);
      }, [searchInput]);

      React.useEffect(() => {
        const query = toParams(state, defaults).toString();
        history.replace({ pathname: ROUTE, search: query ? `?${query}` : "" });
      }, [state.search, state.min, state.op, state.page, state.pageSize, defaultMinimum]);

      React.useEffect(() => {
        if (!explicitMinimum.current) setState((old) => old.min === defaultMinimum ? old : { ...old, min: defaultMinimum, page: 1 });
      }, [defaultMinimum]);

      React.useEffect(() => {
        const request = ++requestRef.current;
        const controller = new AbortController();
        let cancelled = false;
        setPhase("loading"); setError(null); setIndex([]); setScenes([]); setProgress({ loaded: 0, total: 0 });
        (async function () {
          let page = 1, total = null, rows = [], partialError = null;
          while (total === null || rows.length < total) {
            try {
              const response = await client.query({ query: INDEX_QUERY, variables: { filter: { q: state.search || undefined, page, per_page: INDEX_BATCH_SIZE, sort: "id", direction: "ASC" }, sceneFilter: { custom_fields: [scoreCriterion(state.min, state.op)] } }, fetchPolicy: "network-only", context: { fetchOptions: { signal: controller.signal } } });
              if (cancelled || request !== requestRef.current) return;
              const found = response.data.findScenes;
              total = found.count;
              rows = rows.concat(found.scenes);
              setProgress({ loaded: rows.length, total });
              if (!found.scenes.length) break;
              page += 1;
            } catch (caught) {
              partialError = caught;
              break;
            }
          }
          if (cancelled || request !== requestRef.current) return;
          if (partialError && rows.length === 0) { setError(partialError); setPhase("index-error"); return; }
          const parsed = rows.map((scene) => ({ id: String(scene.id), score: parseScore(scene.custom_fields && scene.custom_fields.restash_score) })).sort(compareEntries);
          setIndex(parsed);
          setError(partialError);
          setPhase(partialError ? "partial" : "indexed");
        })();
        return () => { cancelled = true; controller.abort(); };
      }, [state.search, state.min, state.op, indexRevision]);

      const filtered = React.useMemo(() => filterEntries(index, state.min, state.op), [index, state.min, state.op]);
      const pageCount = Math.max(1, Math.ceil(filtered.length / state.pageSize));
      const actualPage = Math.min(state.page, pageCount);
      const pageEntries = React.useMemo(() => paginate(filtered, actualPage, state.pageSize), [filtered, actualPage, state.pageSize]);

      React.useEffect(() => { if (actualPage !== state.page) setState((old) => ({ ...old, page: actualPage })); }, [actualPage, state.page]);
      React.useEffect(() => {
        if (!pageEntries.length) { setScenes([]); return; }
        const request = requestRef.current;
        const controller = new AbortController();
        const ids = pageEntries.map((entry) => entry.id);
        setScenes([]);
        client.query({ query: Api.GQL.FindScenesDocument, variables: { scene_ids: ids.map(Number), filter: { per_page: ids.length } }, fetchPolicy: "network-only", context: { fetchOptions: { signal: controller.signal } } })
          .then((response) => { if (request === requestRef.current) { setScenes(orderHydrated(ids, response.data.findScenes.scenes)); if (phase === "indexed") setPhase("ready"); } })
          .catch((caught) => { if (!controller.signal.aborted && request === requestRef.current) { setError(caught); setPhase("detail-error"); } });
        return () => controller.abort();
      }, [pageEntries.map((entry) => entry.id).join(",")]);

      React.useEffect(() => {
        markedScores.clear();
        pageEntries.forEach((entry) => markedScores.set(entry.id, entry.score));
        return () => markedScores.clear();
      }, [pageEntries]);

      function change(patch) { setState((old) => ({ ...old, ...patch })); }
      async function runTask(name) {
        setTaskRun({ name, status: "SUBMITTING" });
        try {
          const response = await client.mutate({ mutation: Api.GQL.RunPluginTaskDocument, variables: { plugin_id: "restash", task_name: name } });
          setTaskRun({ name, id: String(response.data.runPluginTask), status: "READY" });
        } catch (caught) {
          setTaskRun({ name, status: "FAILED", error: caught.message });
        }
      }
      function select(id, selected, shiftKey) {
        setSelectedIds((old) => { const next = new Set(old); selected ? next.add(id) : next.delete(id); return next; });
      }
      const NativeSceneList = Api.components.SceneList;
      const NativePagination = Api.components.Pagination;
      const NativePaginationIndex = Api.components.PaginationIndex;
      const setPage = (page) => change({ page: Math.max(1, Math.min(pageCount, page)) });
      const taskActive = !!taskRun && ["SUBMITTING", "READY", "RUNNING", "STOPPING"].includes(taskRun.status);
      const taskMessage = taskRun && `${taskRun.name}: ${taskRun.status.toLowerCase()}${["READY", "RUNNING"].includes(taskRun.status) && typeof taskRun.progress === "number" ? ` (${Math.round(taskRun.progress * 100)}%)` : ""}${taskRun.error ? ` — ${taskRun.error}` : ""}`;
      const sceneListFilter = React.useMemo(() => {
        const filter = { displayMode, zoomIndex, currentPage: actualPage, itemsPerPage: state.pageSize };
        filter.getEncodedParams = () => ({});
        filter.clone = () => ({ ...filter });
        return filter;
      }, [displayMode, zoomIndex, actualPage, state.pageSize]);
      return h("main", { className: "restash-freshness container-fluid", "data-testid": "freshness-page" },
        h("div", { className: "restash-heading" },
          h("div", null, h("h2", null, h(FA.FontAwesomeIcon, { icon: icons.faLeaf }), " Fresh scenes"), h("p", null, "Scenes ordered by the canonical restash_score custom field.")),
          h(Bootstrap.ButtonGroup, { className: "restash-task-actions" },
            h(Bootstrap.Button, { variant: "secondary", disabled: taskActive, onClick: () => runTask("Quick Refresh") }, "Quick Refresh"),
            h(Bootstrap.Button, { variant: "secondary", disabled: taskActive, onClick: () => runTask("Recompute All") }, "Recompute All"))),
        h(Bootstrap.Form, { className: "restash-controls", onSubmit: (event) => event.preventDefault() },
          h(Bootstrap.Form.Group, { className: "restash-search-control" }, h(Bootstrap.Form.Label, { className: "sr-only" }, "Search"), h(Bootstrap.Form.Control, { className: "clearable-text-field", value: searchInput, onChange: (event) => setSearchInput(event.target.value), placeholder: "Search scenes" })),
          h(Bootstrap.Form.Group, { className: "restash-minimum-selector" }, h(Bootstrap.Form.Label, { className: "sr-only" }, "Minimum score"), h(Bootstrap.InputGroup, null,
            h(Bootstrap.InputGroup.Prepend, null,
              h(Bootstrap.InputGroup.Text, { className: "bg-secondary text-white border-secondary" },
                h(FA.FontAwesomeIcon, { icon: icons.faLeaf, className: "restash-minimum-icon" }), "Fresh"),
              h(Bootstrap.Dropdown, { as: Bootstrap.ButtonGroup },
              h(Bootstrap.Dropdown.Toggle, { className: "restash-operator bg-secondary text-white border-secondary", title: "Freshness comparison", "aria-label": "Freshness comparison" },
                FILTER_OPERATORS[state.op]),
              h(Bootstrap.Dropdown.Menu, null, Object.entries(FILTER_OPERATORS).map(([op, symbol]) =>
                h(Bootstrap.Dropdown.Item, { key: op, active: state.op === op, onClick: () => change({ op, page: 1 }) }, symbol))))),
            h(Bootstrap.Form.Control, { className: "bg-secondary text-white border-secondary", type: "number", min: 1, max: 100, value: state.min, title: "Minimum score", "aria-label": "Minimum score", onInput: (event) => { explicitMinimum.current = true; change({ min: Math.max(1, Math.min(100, Number(event.currentTarget.value) || 1)), page: 1 }); } }))),
          h(Bootstrap.Form.Group, { className: "page-size-selector" }, h(Bootstrap.Form.Label, { className: "sr-only" }, "Page size"), h(Bootstrap.Form.Control, { className: "btn-secondary", as: "select", value: state.pageSize, title: "Page size", "aria-label": "Page size", onChange: (event) => change({ pageSize: Number(event.target.value), page: 1 }) }, PAGE_SIZES.map((size) => h("option", { key: size }, size)))),
          h(Bootstrap.ButtonGroup, { className: "restash-display-modes" },
            h(Bootstrap.Button, { variant: "secondary", active: displayMode === 0, title: "Grid", "aria-label": "Grid view", onClick: () => setDisplayMode(0) }, h(FA.FontAwesomeIcon, { icon: icons.faThLarge })),
            h(Bootstrap.Button, { variant: "secondary", active: displayMode === 1, title: "List", "aria-label": "List view", onClick: () => setDisplayMode(1) }, h(FA.FontAwesomeIcon, { icon: icons.faList })),
            h(Bootstrap.Button, { variant: "secondary", active: displayMode === 2, title: "Wall", "aria-label": "Wall view", onClick: () => setDisplayMode(2) }, h(FA.FontAwesomeIcon, { icon: icons.faSquare }))),
          displayMode !== 1 && h("div", { className: "zoom-slider-container", title: "Card size" },
            h(Bootstrap.Form.Control, { className: "zoom-slider", type: "range", min: 0, max: 3, value: zoomIndex, "aria-label": "Card size", onChange: (event) => setZoomIndex(Number.parseInt(event.currentTarget.value, 10)) }))),
        phase === "loading" && h(Status, null, `Indexing scenes… ${progress.loaded}${progress.total ? ` / ${progress.total}` : ""}`),
        phase === "index-error" && h(Status, { variant: "danger" }, `Could not fetch the freshness index: ${error.message}`),
        phase === "partial" && h(Status, { variant: "warning" }, `Only ${progress.loaded} of ${progress.total || "?"} scenes were indexed: ${error.message}`),
        phase === "detail-error" && h(Status, { variant: "danger" }, `Could not load scene cards: ${error.message}`),
        taskRun && h(Status, { variant: taskRun.status === "FAILED" ? "danger" : taskRun.status === "FINISHED" ? "success" : "info" }, taskMessage),
        phase !== "loading" && filtered.length === 0 && h(Status, null, "No scenes match these freshness filters."),
        filtered.length > 0 && !loadingComponents && NativePagination && NativePaginationIndex && h("div", { className: "pagination-index-container" },
          h(NativePagination, { currentPage: actualPage, itemsPerPage: state.pageSize, totalItems: filtered.length, onChangePage: setPage }),
          h(NativePaginationIndex, { itemsPerPage: state.pageSize, currentPage: actualPage, totalItems: filtered.length })),
        scenes.length > 0 && loadingComponents && h(Status, null, "Loading scene-card components…"),
        scenes.length > 0 && !loadingComponents && !NativeSceneList && h(Status, { variant: "danger" }, "Stash did not provide its native scene-list component."),
        scenes.length > 0 && !loadingComponents && NativeSceneList && h(NativeSceneList, { scenes, filter: sceneListFilter, selectedIds, onSelectChange: select }),
        filtered.length > state.pageSize && !loadingComponents && NativePagination && h("div", { className: "pagination-footer-container" },
          h("div", { className: "pagination-footer" },
            h(NativePagination, { itemsPerPage: state.pageSize, currentPage: actualPage, totalItems: filtered.length, onChangePage: setPage, pagePopupPlacement: "top" }))));
    }

    Api.register.route(ROUTE, FreshnessPage);
    Api.register.route(LEGACY_ROUTE, FreshnessPage);
  }

  return { DEFAULTS, FILTER_OPERATORS, PAGE_SIZES, ROUTE, LEGACY_ROUTE, parseScore, compareEntries, matchesFilter, filterEntries, scoreCriterion, paginate, orderHydrated, normalizeParams, toParams, initialize };
});
