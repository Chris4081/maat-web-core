let currentChatId = null;
let stateCache = null;
let ggufModelsLoaded = false;
let ggufModelsCache = [];
let chatsCache = [];
let isSending = false;
let inputIsComposing = false;
let pendingAttachments = [];
let activeSpeakButton = null;
let activeSpeechMode = null;
let projectsLoaded = false;
let docsLoaded = false;
let personGraphCache = { entries: [], selectedId: "" };
let currentAbortController = null;
const activeStreams = new Map();

const PASTE_ATTACHMENT_THRESHOLD = 1600;
const PASTE_ATTACHMENT_MIN_LINES = 20;
const THEME_STORAGE_KEY = "maat-web-theme-mode";

const messagesEl = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const input = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const statusLine = document.querySelector("#statusLine");
const attachmentTray = document.querySelector("#attachmentTray");
const chatListEl = document.querySelector("#chatList");
const chatSearch = document.querySelector("#chatSearch");
const chatLogEl = document.querySelector("#chatLog");
const chatHelpEl = document.querySelector("#chatHelp");
const chatProjectsEl = document.querySelector("#chatProjects");
const chatDocsEl = document.querySelector("#chatDocs");
const chatViewChat = document.querySelector("#chatViewChat");
const chatViewLog = document.querySelector("#chatViewLog");
const chatViewHelp = document.querySelector("#chatViewHelp");
const chatViewProjects = document.querySelector("#chatViewProjects");
const chatViewDocs = document.querySelector("#chatViewDocs");
const chatCurrentUser = document.querySelector("#chatCurrentUser");
const chatModelMenuButton = document.querySelector("#chatModelMenuButton");
const chatFavoriteModel = document.querySelector("#chatFavoriteModel");
const chatThinkingToggle = document.querySelector("#chatThinkingToggle");
const themeModeSelect = document.querySelector("#themeMode");
const maatThinkOff = document.querySelector("#maatThinkOff");
const maatThinkSlider = document.querySelector("#maatThinkSlider");
const maatThinkSliderValue = document.querySelector("#maatThinkSliderValue");
const maatThinkingLevel = document.querySelector("#maatThinkingLevel");
const maatThinkingLevelValue = document.querySelector("#maatThinkingLevelValue");
const maatThinkingOff = document.querySelector("#maatThinkingOff");
const maatThinkingStatus = document.querySelector("#maatThinkingStatus");
const saveMaatStatus = document.querySelector("#saveMaatStatus");
const saveModelStatus = document.querySelector("#saveModelStatus");
const saveSettingsStatus = document.querySelector("#saveSettingsStatus");
const savePromptStatus = document.querySelector("#savePromptStatus");
const restartWebCore = document.querySelector("#restartWebCore");
const loaderAutoMode = document.querySelector("#loaderAutoMode");
const loaderManualMode = document.querySelector("#loaderManualMode");
const runSystemScan = document.querySelector("#runSystemScan");
const systemScanStatus = document.querySelector("#systemScanStatus");
const systemScanSummary = document.querySelector("#systemScanSummary");
const llamaModelPathInput = document.querySelector("#llamaModelPath");
const ggufModelDirsCustom = document.querySelector("#ggufModelDirsCustom");
const settingsLlamaModelPath = document.querySelector("#settingsLlamaModelPath");
const applySettingsModelPath = document.querySelector("#applySettingsModelPath");
const chatCompressorEnabled = document.querySelector("#chatCompressorEnabled");
const chatCompressorAutoTitle = document.querySelector("#chatCompressorAutoTitle");
const chatCompressorPersistSummary = document.querySelector("#chatCompressorPersistSummary");
const chatCompressorTriggerTurns = document.querySelector("#chatCompressorTriggerTurns");
const chatCompressorKeepRecentTurns = document.querySelector("#chatCompressorKeepRecentTurns");
const chatCompressorThreshold = document.querySelector("#chatCompressorThreshold");
const chatCompressorMaxChars = document.querySelector("#chatCompressorMaxChars");
const chatCompressorDebug = document.querySelector("#chatCompressorDebug");
const contextOptimizerEnabled = document.querySelector("#contextOptimizerEnabled");
const contextOptimizerDebug = document.querySelector("#contextOptimizerDebug");
const contextOptimizerUserBlock = document.querySelector("#contextOptimizerUserBlock");
const contextOptimizerMaxMemoryItems = document.querySelector("#contextOptimizerMaxMemoryItems");
const contextOptimizerMaxMemoryChars = document.querySelector("#contextOptimizerMaxMemoryChars");
const contextOptimizerStatus = document.querySelector("#contextOptimizerStatus");
const supermemEnabled = document.querySelector("#supermemEnabled");
const supermemAutostore = document.querySelector("#supermemAutostore");
const supermemAutorecall = document.querySelector("#supermemAutorecall");
const supermemDebug = document.querySelector("#supermemDebug");
const supermemModelSaves = document.querySelector("#supermemModelSaves");
const supermemSaveBox = document.querySelector("#supermemSaveBox");
const supermemDreaming = document.querySelector("#supermemDreaming");
const supermemDreamOnLoad = document.querySelector("#supermemDreamOnLoad");
const supermemArchive = document.querySelector("#supermemArchive");
const supermemPersonRecall = document.querySelector("#supermemPersonRecall");
const supermemPersonGraph = document.querySelector("#supermemPersonGraph");
const supermemCurrentUser = document.querySelector("#supermemCurrentUser");
const supermemNewUser = document.querySelector("#supermemNewUser");
const supermemAddUser = document.querySelector("#supermemAddUser");
const supermemTopK = document.querySelector("#supermemTopK");
const supermemMinScore = document.querySelector("#supermemMinScore");
const supermemGraphTopK = document.querySelector("#supermemGraphTopK");
const supermemPersonTopK = document.querySelector("#supermemPersonTopK");
const supermemUserBonus = document.querySelector("#supermemUserBonus");
const supermemMaxMemories = document.querySelector("#supermemMaxMemories");
const supermemDreamHours = document.querySelector("#supermemDreamHours");
const supermemArchiveDays = document.querySelector("#supermemArchiveDays");
const supermemRunDream = document.querySelector("#supermemRunDream");
const supermemDreamStatus = document.querySelector("#supermemDreamStatus");
const supermemKnownUsers = document.querySelector("#supermemKnownUsers");
const supermemPersonNames = document.querySelector("#supermemPersonNames");
const supermemAmbiguousNames = document.querySelector("#supermemAmbiguousNames");
const supermemStatus = document.querySelector("#supermemStatus");
const personGraphSourceUser = document.querySelector("#personGraphSourceUser");
const personGraphRefresh = document.querySelector("#personGraphRefresh");
const personGraphNew = document.querySelector("#personGraphNew");
const personGraphSelect = document.querySelector("#personGraphSelect");
const personGraphTarget = document.querySelector("#personGraphTarget");
const personGraphRelation = document.querySelector("#personGraphRelation");
const personGraphEmotion = document.querySelector("#personGraphEmotion");
const personGraphField = document.querySelector("#personGraphField");
const personGraphStatusSelect = document.querySelector("#personGraphStatusSelect");
const personGraphMaturity = document.querySelector("#personGraphMaturity");
const personGraphStrength = document.querySelector("#personGraphStrength");
const personGraphConfidence = document.querySelector("#personGraphConfidence");
const personGraphEvidenceCount = document.querySelector("#personGraphEvidenceCount");
const personGraphTags = document.querySelector("#personGraphTags");
const personGraphEvidence = document.querySelector("#personGraphEvidence");
const personGraphSave = document.querySelector("#personGraphSave");
const personGraphDelete = document.querySelector("#personGraphDelete");
const personGraphStatus = document.querySelector("#personGraphStatus");
const personGraphList = document.querySelector("#personGraphList");
const spiritEnabled = document.querySelector("#spiritEnabled");
const spiritMode = document.querySelector("#spiritMode");
const spiritLanguage = document.querySelector("#spiritLanguage");
const spiritOnce = document.querySelector("#spiritOnce");
const spiritUseEmojis = document.querySelector("#spiritUseEmojis");
const spiritStatus = document.querySelector("#spiritStatus");
const styleEnabled = document.querySelector("#styleEnabled");
const styleGreetingOverride = document.querySelector("#styleGreetingOverride");
const styleToneAuto = document.querySelector("#styleToneAuto");
const styleToneMode = document.querySelector("#styleToneMode");
const styleOpeningMode = document.querySelector("#styleOpeningMode");
const styleDensityMode = document.querySelector("#styleDensityMode");
const styleHeadingMode = document.querySelector("#styleHeadingMode");
const styleListMode = document.querySelector("#styleListMode");
const styleEmojiMode = document.querySelector("#styleEmojiMode");
const styleOldSmileyMode = document.querySelector("#styleOldSmileyMode");
const styleStatus = document.querySelector("#styleStatus");
const styleDebug = document.querySelector("#styleDebug");
const rewriteEnabled = document.querySelector("#rewriteEnabled");
const rewriteTrimOutputs = document.querySelector("#rewriteTrimOutputs");
const rewriteShowBanner = document.querySelector("#rewriteShowBanner");
const rewriteMode = document.querySelector("#rewriteMode");
const rewriteFieldWeak = document.querySelector("#rewriteFieldWeak");
const rewriteFieldStrong = document.querySelector("#rewriteFieldStrong");
const rewriteRMin = document.querySelector("#rewriteRMin");
const rewriteStatus = document.querySelector("#rewriteStatus");
const coreEnabled = document.querySelector("#coreEnabled");
const coreMode = document.querySelector("#coreMode");
const coreStatus = document.querySelector("#coreStatus");
const realityEnabled = document.querySelector("#realityEnabled");
const realityInjectTime = document.querySelector("#realityInjectTime");
const realityShowBanner = document.querySelector("#realityShowBanner");
const realityStatus = document.querySelector("#realityStatus");
const balanceEnabled = document.querySelector("#balanceEnabled");
const balanceDebug = document.querySelector("#balanceDebug");
const balanceOnce = document.querySelector("#balanceOnce");
const balanceSelfReflect = document.querySelector("#balanceSelfReflect");
const balanceDynamic = document.querySelector("#balanceDynamic");
const balanceContextWeights = document.querySelector("#balanceContextWeights");
const balanceCounterpartMode = document.querySelector("#balanceCounterpartMode");
const balanceLevel = document.querySelector("#balanceLevel");
const balanceStatus = document.querySelector("#balanceStatus");
const claimGuardEnabled = document.querySelector("#claimGuardEnabled");
const claimGuardAfterOutput = document.querySelector("#claimGuardAfterOutput");
const claimGuardBanner = document.querySelector("#claimGuardBanner");
const claimGuardMode = document.querySelector("#claimGuardMode");
const claimGuardStatus = document.querySelector("#claimGuardStatus");
const adaptiveLearningEnabled = document.querySelector("#adaptiveLearningEnabled");
const adaptiveLearningInject = document.querySelector("#adaptiveLearningInject");
const adaptiveLearningDebug = document.querySelector("#adaptiveLearningDebug");
const adaptiveLearningPerTurn = document.querySelector("#adaptiveLearningPerTurn");
const adaptiveLearningExplore = document.querySelector("#adaptiveLearningExplore");
const adaptiveLearningUserBonus = document.querySelector("#adaptiveLearningUserBonus");
const adaptiveLearningStatus = document.querySelector("#adaptiveLearningStatus");
const feedbackEnabled = document.querySelector("#feedbackEnabled");
const feedbackDebug = document.querySelector("#feedbackDebug");
const feedbackSelfLearning = document.querySelector("#feedbackSelfLearning");
const feedbackHistoryLimit = document.querySelector("#feedbackHistoryLimit");
const feedbackWarnB = document.querySelector("#feedbackWarnB");
const feedbackWarnR = document.querySelector("#feedbackWarnR");
const feedbackWarnH = document.querySelector("#feedbackWarnH");
const feedbackSelfPerReport = document.querySelector("#feedbackSelfPerReport");
const feedbackStatus = document.querySelector("#feedbackStatus");
const projectMemoryEnabled = document.querySelector("#projectMemoryEnabled");
const projectMemoryDebug = document.querySelector("#projectMemoryDebug");
const projectMemoryTopK = document.querySelector("#projectMemoryTopK");
const projectMemoryMaxChars = document.querySelector("#projectMemoryMaxChars");
const projectSettingsSave = document.querySelector("#projectSettingsSave");
const projectSettingsStatus = document.querySelector("#projectSettingsStatus");
const projectRefresh = document.querySelector("#projectRefresh");
const projectNew = document.querySelector("#projectNew");
const projectSearch = document.querySelector("#projectSearch");
const projectSelect = document.querySelector("#projectSelect");
const projectOpen = document.querySelector("#projectOpen");
const projectSearchResults = document.querySelector("#projectSearchResults");
const projectName = document.querySelector("#projectName");
const projectVersion = document.querySelector("#projectVersion");
const projectStatus = document.querySelector("#projectStatus");
const projectTags = document.querySelector("#projectTags");
const projectTriggers = document.querySelector("#projectTriggers");
const projectDescription = document.querySelector("#projectDescription");
const projectContext = document.querySelector("#projectContext");
const projectSave = document.querySelector("#projectSave");
const projectStatusText = document.querySelector("#projectStatusText");
const projectPreview = document.querySelector("#projectPreview");
const projectFormulaName = document.querySelector("#projectFormulaName");
const projectFormulaDescription = document.querySelector("#projectFormulaDescription");
const projectFormulaText = document.querySelector("#projectFormulaText");
const projectFormulaAdd = document.querySelector("#projectFormulaAdd");
const projectPaperTitle = document.querySelector("#projectPaperTitle");
const projectPaperRef = document.querySelector("#projectPaperRef");
const projectPaperNotes = document.querySelector("#projectPaperNotes");
const projectPaperAdd = document.querySelector("#projectPaperAdd");
const projectEntryType = document.querySelector("#projectEntryType");
const projectEntryTags = document.querySelector("#projectEntryTags");
const projectEntryText = document.querySelector("#projectEntryText");
const projectEntryAdd = document.querySelector("#projectEntryAdd");
const fileBuilderEnabled = document.querySelector("#fileBuilderEnabled");
const fileBuilderInject = document.querySelector("#fileBuilderInject");
const fileBuilderReplace = document.querySelector("#fileBuilderReplace");
const fileBuilderSource = document.querySelector("#fileBuilderSource");
const fileBuilderFences = document.querySelector("#fileBuilderFences");
const fileBuilderCompileTex = document.querySelector("#fileBuilderCompileTex");
const fileBuilderPythonCheck = document.querySelector("#fileBuilderPythonCheck");
const fileBuilderPythonRun = document.querySelector("#fileBuilderPythonRun");
const fileBuilderTerminal = document.querySelector("#fileBuilderTerminal");
const fileBuilderFeedback = document.querySelector("#fileBuilderFeedback");
const fileBuilderDebug = document.querySelector("#fileBuilderDebug");
const fileBuilderPreviewChars = document.querySelector("#fileBuilderPreviewChars");
const docsSettingsSave = document.querySelector("#docsSettingsSave");
const docsSettingsStatus = document.querySelector("#docsSettingsStatus");
const docsRefresh = document.querySelector("#docsRefresh");
const docsRoot = document.querySelector("#docsRoot");
const docsSelect = document.querySelector("#docsSelect");
const docsDownload = document.querySelector("#docsDownload");
const docsOpenFile = document.querySelector("#docsOpenFile");
const docsPdfDownload = document.querySelector("#docsPdfDownload");
const docsOpenPdf = document.querySelector("#docsOpenPdf");
const docsRunPython = document.querySelector("#docsRunPython");
const docsDelete = document.querySelector("#docsDelete");
const docsStatus = document.querySelector("#docsStatus");
const docsFilename = document.querySelector("#docsFilename");
const docsContent = document.querySelector("#docsContent");
const docsRunArgs = document.querySelector("#docsRunArgs");
const docsSave = document.querySelector("#docsSave");
const docsSaveStatus = document.querySelector("#docsSaveStatus");
const docsRunOutput = document.querySelector("#docsRunOutput");
const docsPreview = document.querySelector("#docsPreview");
const emotionEnabled = document.querySelector("#emotionEnabled");
const emotionDebug = document.querySelector("#emotionDebug");
const emotionMode = document.querySelector("#emotionMode");
const emotionLanguage = document.querySelector("#emotionLanguage");
const emotionStatus = document.querySelector("#emotionStatus");
const offlineWikiEnabled = document.querySelector("#offlineWikiEnabled");
const offlineWikiAuto = document.querySelector("#offlineWikiAuto");
const offlineWikiDebug = document.querySelector("#offlineWikiDebug");
const offlineWikiLog = document.querySelector("#offlineWikiLog");
const offlineWikiPath = document.querySelector("#offlineWikiPath");
const offlineWikiMaxChars = document.querySelector("#offlineWikiMaxChars");
const offlineWikiMultiMaxChars = document.querySelector("#offlineWikiMultiMaxChars");
const offlineWikiMaxTerms = document.querySelector("#offlineWikiMaxTerms");
const offlineWikiStatus = document.querySelector("#offlineWikiStatus");
const identityEnabled = document.querySelector("#identityEnabled");
const identityOnce = document.querySelector("#identityOnce");
const identityName = document.querySelector("#identityName");
const identityMode = document.querySelector("#identityMode");
const identityStatus = document.querySelector("#identityStatus");
const engineEnabled = document.querySelector("#engineEnabled");
const engineShowInChat = document.querySelector("#engineShowInChat");
const engineShowCciDebug = document.querySelector("#engineShowCciDebug");
const advancedCciEnabled = document.querySelector("#advancedCciEnabled");
const advancedCciShowDebug = document.querySelector("#advancedCciShowDebug");
const advancedCciKappa = document.querySelector("#advancedCciKappa");
const engineLastReport = document.querySelector("#engineLastReport");
const reflectionEnabled = document.querySelector("#reflectionEnabled");
const reflectionBanner = document.querySelector("#reflectionBanner");
const reflectionPromptRule = document.querySelector("#reflectionPromptRule");
const reflectionMode = document.querySelector("#reflectionMode");
const reflectionStatus = document.querySelector("#reflectionStatus");
const antihalluEnabled = document.querySelector("#antihalluEnabled");
const antihalluBanner = document.querySelector("#antihalluBanner");
const antihalluGaps = document.querySelector("#antihalluGaps");
const antihalluSymbolic = document.querySelector("#antihalluSymbolic");
const antihalluMode = document.querySelector("#antihalluMode");
const antihalluSoftenThreshold = document.querySelector("#antihalluSoftenThreshold");
const antihalluStrictThreshold = document.querySelector("#antihalluStrictThreshold");
const antihalluStatus = document.querySelector("#antihalluStatus");

function shortPath(path) {
  if (!path) return "";
  const parts = String(path).split("/");
  return parts[parts.length - 1] || path;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function describeModel(settings) {
  if (settings.model_adapter === "llama_cpp_direct") {
    return settings.llama_model_path
      ? `llama.cpp direkt · ${shortPath(settings.llama_model_path)}`
      : "llama.cpp direkt · kein GGUF gesetzt";
  }
  if (settings.model_adapter === "echo") {
    return "Echo-Testmodus";
  }
  return `${settings.api_base} · ${settings.model_name}`;
}

function formatChatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16).replace("T", " ");
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function trimPreview(value, length = 92) {
  const text = stripAttachmentBlocks(value).replace(/\s+/g, " ").trim();
  return text.length > length ? `${text.slice(0, length - 1)}…` : text;
}

function normalizeUserName(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function splitKnownUsers(value) {
  const seen = new Set();
  const users = [];
  for (const item of String(value || "").split(/[,;\n]+/)) {
    const name = normalizeUserName(item);
    const key = name.toLocaleLowerCase("de-DE");
    if (!name || seen.has(key)) continue;
    seen.add(key);
    users.push(name);
  }
  return users;
}

function splitLooseList(value) {
  const seen = new Set();
  const items = [];
  for (const item of String(value || "").split(/[,;\n]+/)) {
    const clean = normalizeUserName(item);
    const key = clean.toLocaleLowerCase("de-DE");
    if (!clean || seen.has(key)) continue;
    seen.add(key);
    items.push(clean);
  }
  return items;
}

function knownUsersFromSettings(settings = stateCache?.settings || {}) {
  const users = splitKnownUsers(settings.supermem_known_users || "");
  for (const name of ["User", normalizeUserName(settings.supermem_current_user || "")]) {
    if (!name) continue;
    const exists = users.some((item) => item.toLocaleLowerCase("de-DE") === name.toLocaleLowerCase("de-DE"));
    if (!exists) users.unshift(name);
  }
  return users.length ? users : ["User"];
}

function personGraphSelectedUser() {
  return normalizeUserName(personGraphSourceUser?.value || selectedMemoryUser() || "User");
}

function renderUserSelect(select, users, currentUser) {
  if (!select) return;
  const current = normalizeUserName(currentUser || "User");
  select.innerHTML = "";
  for (const name of users) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  }
  const hasCurrent = users.some((name) => name.toLocaleLowerCase("de-DE") === current.toLocaleLowerCase("de-DE"));
  select.value = hasCurrent ? users.find((name) => name.toLocaleLowerCase("de-DE") === current.toLocaleLowerCase("de-DE")) : users[0];
}

function syncKnownUsersField(settings = stateCache?.settings || {}) {
  if (!supermemKnownUsers) return;
  supermemKnownUsers.value = knownUsersFromSettings(settings).join(", ");
}

function selectedMemoryUser() {
  return normalizeUserName(supermemCurrentUser?.value || chatCurrentUser?.value || stateCache?.settings?.supermem_current_user || "User");
}

function setPersonGraphStatus(text, isError = false) {
  if (!personGraphStatus) return;
  personGraphStatus.textContent = text;
  personGraphStatus.classList.toggle("error-text", Boolean(isError));
}

function blankPersonGraphForm() {
  if (personGraphSelect) personGraphSelect.value = "";
  if (personGraphTarget) personGraphTarget.value = "";
  if (personGraphRelation) personGraphRelation.value = "";
  if (personGraphEmotion) personGraphEmotion.value = "neutral";
  if (personGraphField) personGraphField.value = "V";
  if (personGraphStatusSelect) personGraphStatusSelect.value = "confirmed";
  if (personGraphMaturity) personGraphMaturity.value = "NEW";
  if (personGraphStrength) personGraphStrength.value = "1";
  if (personGraphConfidence) personGraphConfidence.value = "1";
  if (personGraphEvidenceCount) personGraphEvidenceCount.value = "1";
  if (personGraphTags) personGraphTags.value = "";
  if (personGraphEvidence) personGraphEvidence.value = "";
  setPersonGraphStatus("Neuer Person-Graph-Eintrag.");
}

function fillPersonGraphForm(entry = null) {
  if (!entry) {
    blankPersonGraphForm();
    return;
  }
  if (personGraphSelect) personGraphSelect.value = String(entry.id || "");
  if (personGraphTarget) personGraphTarget.value = entry.target_person || "";
  if (personGraphRelation) personGraphRelation.value = entry.relation || "";
  if (personGraphEmotion) personGraphEmotion.value = entry.emotion || "neutral";
  if (personGraphField) personGraphField.value = entry.maat_field || "V";
  if (personGraphStatusSelect) personGraphStatusSelect.value = entry.relation_status || "confirmed";
  if (personGraphMaturity) personGraphMaturity.value = entry.maturity || "NEW";
  if (personGraphStrength) personGraphStrength.value = Number(entry.strength ?? 1).toFixed(2);
  if (personGraphConfidence) personGraphConfidence.value = Number(entry.confidence ?? 1).toFixed(2);
  if (personGraphEvidenceCount) personGraphEvidenceCount.value = entry.evidence_count || 1;
  if (personGraphTags) personGraphTags.value = entry.tags || "";
  if (personGraphEvidence) personGraphEvidence.value = entry.last_evidence || "";
  setPersonGraphStatus(`Geöffnet: ${entry.summary || entry.target_person || "Person"}`);
}

function renderPersonGraph(data = {}) {
  const entries = Array.isArray(data.entries) ? data.entries : [];
  personGraphCache = {
    entries,
    selectedId: String(data.selected_id || personGraphSelect?.value || ""),
  };
  const settings = stateCache?.settings || {};
  const users = knownUsersFromSettings(settings);
  const current = normalizeUserName(data.source_user || personGraphSelectedUser() || settings.supermem_current_user || "User");
  renderUserSelect(personGraphSourceUser, users, current);

  if (personGraphSelect) {
    const previous = personGraphCache.selectedId;
    personGraphSelect.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = entries.length ? "Neuen Eintrag anlegen" : "Keine Einträge";
    personGraphSelect.appendChild(empty);
    for (const entry of entries) {
      const option = document.createElement("option");
      option.value = String(entry.id || "");
      option.textContent = entry.summary || `${entry.target_person || "Person"} · ${entry.relation || "Relation"}`;
      personGraphSelect.appendChild(option);
    }
    const chosen = entries.find((entry) => String(entry.id) === previous) ? previous : "";
    personGraphSelect.value = chosen;
  }

  if (personGraphList) {
    personGraphList.textContent = entries.length
      ? entries.map((entry, index) => `${index + 1}. ${entry.summary}\n   ${entry.last_evidence || ""}`).join("\n")
      : `Kein Person-Graph-Eintrag für ${current}.`;
  }

  const selected = entries.find((entry) => String(entry.id) === String(personGraphSelect?.value || ""));
  if (selected) {
    fillPersonGraphForm(selected);
  } else if (!entries.length || data.selected_id) {
    const created = entries.find((entry) => String(entry.id) === String(data.selected_id || ""));
    fillPersonGraphForm(created || null);
  }

  if (!data.ok && data.error) {
    setPersonGraphStatus(data.error, true);
  } else if (entries.length) {
    setPersonGraphStatus(`Person Graph geladen · ${entries.length} Einträge für ${current}`);
  } else {
    setPersonGraphStatus(`Person Graph leer für ${current}.`);
  }
}

async function loadPersonGraph(sourceUser = "") {
  if (!personGraphSelect && !personGraphList) return;
  const user = normalizeUserName(sourceUser || personGraphSelectedUser() || selectedMemoryUser());
  try {
    const data = await fetchJson(`/api/super-memory/person-graph?source_user=${encodeURIComponent(user)}`);
    renderPersonGraph(data);
  } catch (error) {
    setPersonGraphStatus(error.message || "Person Graph konnte nicht geladen werden.", true);
  }
}

function personGraphPayload() {
  return {
    id: personGraphSelect?.value || "",
    source_user: personGraphSelectedUser(),
    target_person: personGraphTarget?.value?.trim() || "",
    relation: personGraphRelation?.value?.trim() || "erwähnte Person",
    emotion: personGraphEmotion?.value?.trim() || "neutral",
    maat_field: personGraphField?.value || "V",
    relation_status: personGraphStatusSelect?.value || "confirmed",
    maturity: personGraphMaturity?.value || "NEW",
    strength: Number(personGraphStrength?.value || 1),
    confidence: Number(personGraphConfidence?.value || 1),
    evidence_count: Number(personGraphEvidenceCount?.value || 1),
    tags: personGraphTags?.value?.trim() || "",
    last_evidence: personGraphEvidence?.value?.trim() || "",
  };
}

async function savePersonGraphEntry() {
  const payload = personGraphPayload();
  if (!payload.target_person) {
    setPersonGraphStatus("Bitte eine Person eintragen.", true);
    return;
  }
  try {
    const data = await postJson("/api/super-memory/person-graph/save", payload);
    if (data.settings) {
      stateCache.settings = data.settings;
      updateSuperMemoryControls(data.settings, stateCache);
    }
    renderPersonGraph(data);
    setPersonGraphStatus(data.ok ? "Person Graph gespeichert." : data.error || "Speichern fehlgeschlagen.", !data.ok);
  } catch (error) {
    setPersonGraphStatus(error.message || "Speichern fehlgeschlagen.", true);
  }
}

async function deletePersonGraphEntry() {
  const id = personGraphSelect?.value || "";
  if (!id) {
    setPersonGraphStatus("Kein Eintrag ausgewählt.", true);
    return;
  }
  if (!confirm("Person-Graph-Eintrag nur aus der Datenbank löschen?")) return;
  try {
    const data = await postJson("/api/super-memory/person-graph/delete", {
      id,
      source_user: personGraphSelectedUser(),
    });
    renderPersonGraph(data);
    setPersonGraphStatus(data.ok ? "Person Graph gelöscht." : data.error || "Löschen fehlgeschlagen.", !data.ok);
  } catch (error) {
    setPersonGraphStatus(error.message || "Löschen fehlgeschlagen.", true);
  }
}

function normalizeThemeMode(value) {
  return ["auto", "light", "dark"].includes(value) ? value : "auto";
}

function autoThemeForDate(date = new Date()) {
  const hour = date.getHours();
  return hour >= 19 || hour < 8 ? "dark" : "light";
}

function themeLabel(theme, mode) {
  if (mode === "auto") {
    return theme === "dark" ? "Auto: dunkel bis 08:00" : "Auto: hell bis 19:00";
  }
  return theme === "dark" ? "Dunkles Design" : "Helles Design";
}

function applyThemeMode(mode = localStorage.getItem(THEME_STORAGE_KEY) || "auto", announce = false) {
  const normalized = normalizeThemeMode(mode);
  const theme = normalized === "auto" ? autoThemeForDate() : normalized;
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.themeMode = normalized;
  if (themeModeSelect) themeModeSelect.value = normalized;
  if (announce && statusLine) {
    statusLine.textContent = themeLabel(theme, normalized);
  }
  return { mode: normalized, theme };
}

function initThemeScheduler() {
  applyThemeMode(localStorage.getItem(THEME_STORAGE_KEY) || "auto");
  window.setInterval(() => {
    const mode = normalizeThemeMode(localStorage.getItem(THEME_STORAGE_KEY) || "auto");
    if (mode === "auto") {
      const before = document.documentElement.dataset.theme;
      const result = applyThemeMode("auto");
      if (before && before !== result.theme && statusLine) {
        statusLine.textContent = themeLabel(result.theme, "auto");
      }
    }
  }, 60 * 1000);
}

function setChatView(view) {
  const next = view === "log" ? "log" : view === "help" ? "help" : view === "projects" ? "projects" : view === "docs" ? "docs" : "chat";
  chatViewChat?.classList.toggle("active", next === "chat");
  chatViewLog?.classList.toggle("active", next === "log");
  chatViewHelp?.classList.toggle("active", next === "help");
  chatViewProjects?.classList.toggle("active", next === "projects");
  chatViewDocs?.classList.toggle("active", next === "docs");
  if (messagesEl) messagesEl.hidden = next !== "chat";
  if (chatLogEl) chatLogEl.hidden = next !== "log";
  if (chatHelpEl) chatHelpEl.hidden = next !== "help";
  if (chatProjectsEl) chatProjectsEl.hidden = next !== "projects";
  if (chatDocsEl) chatDocsEl.hidden = next !== "docs";
  if (next === "chat") {
    scrollMessagesToBottom();
  } else {
    requestAnimationFrame(() => {
      if (next === "log" && chatLogEl) chatLogEl.scrollTop = chatLogEl.scrollHeight;
      if (next === "help" && chatHelpEl) chatHelpEl.scrollTop = 0;
      if (next === "projects" && chatProjectsEl) chatProjectsEl.scrollTop = 0;
      if (next === "docs" && chatDocsEl) chatDocsEl.scrollTop = 0;
    });
    if (next === "help") loadHelpPanel(false);
    if (next === "projects") loadProjectsPanel(false);
    if (next === "docs") loadDocsPanel(false);
  }
}

function renderHelpPanel(payload = {}) {
  if (!chatHelpEl) return;
  const markdown = payload.markdown || "# MAAT Help\n\nKeine Hilfe geladen.";
  chatHelpEl.innerHTML = `<div class="help-card">${renderMarkdown(markdown)}</div>`;
}

let helpLoaded = false;

async function loadHelpPanel(force = false) {
  if (!chatHelpEl || (helpLoaded && !force)) return;
  chatHelpEl.innerHTML = '<div class="help-empty">Help wird geladen...</div>';
  try {
    const response = await fetch("/api/help");
    const data = await response.json();
    renderHelpPanel(data);
    helpLoaded = true;
  } catch (error) {
    chatHelpEl.innerHTML = `<div class="help-empty">Help konnte nicht geladen werden: ${escapeHtml(error.message || error)}</div>`;
  }
}

function listText(values = []) {
  return Array.isArray(values) ? values.join(", ") : String(values || "");
}

function selectedProjectId() {
  return projectSelect?.value || projectName?.dataset.projectId || "";
}

function fillProjectForm(project = null) {
  const item = project || {};
  if (projectName) {
    projectName.value = item.name || "";
    projectName.dataset.projectId = item.id || "";
  }
  if (projectVersion) projectVersion.value = item.version || "";
  if (projectStatus) projectStatus.value = item.status || "aktiv";
  if (projectTags) projectTags.value = listText(item.tags || []);
  if (projectTriggers) projectTriggers.value = listText(item.recall_triggers || []);
  if (projectDescription) projectDescription.value = item.description || "";
  if (projectContext) projectContext.value = item.context || "";
}

function renderProjectSelect(projects = [], selectedId = "") {
  if (!projectSelect) return;
  projectSelect.innerHTML = "";
  for (const project of projects) {
    const option = document.createElement("option");
    option.value = project.id || project.name;
    option.textContent = `${project.name || "Unbenannt"}${project.version ? ` · v${project.version}` : ""}`;
    option.title = `${project.status || "aktiv"} · ${listText(project.tags || [])}`;
    if ((selectedId || "") === option.value) option.selected = true;
    projectSelect.appendChild(option);
  }
}

function renderProjectsPanel(data = {}) {
  stateCache = stateCache || {};
  stateCache.maat_project_memory = data;
  const settings = stateCache.settings || {};
  if (projectMemoryEnabled) projectMemoryEnabled.checked = settings.project_memory_enabled !== false;
  if (projectMemoryDebug) projectMemoryDebug.checked = Boolean(settings.project_memory_debug);
  if (projectMemoryTopK) projectMemoryTopK.value = settings.project_memory_top_k ?? data.top_k ?? 2;
  if (projectMemoryMaxChars) projectMemoryMaxChars.value = settings.project_memory_max_chars ?? data.max_chars ?? 2600;

  const selected = data.selected || null;
  renderProjectSelect(data.projects || [], selected?.id || "");
  fillProjectForm(selected);
  if (projectPreview) {
    const markdown = data.markdown || (selected ? `## ${selected.name}` : "Noch kein Projekt geöffnet.");
    projectPreview.innerHTML = renderMarkdown(markdown);
  }
  if (projectSearchResults) {
    const hits = data.search?.hits || [];
    projectSearchResults.innerHTML = hits.length
      ? hits.map((item) => `<div><strong>${escapeHtml(item.name || "")}</strong> · score ${escapeHtml(item._score ?? item.score ?? "")}</div>`).join("")
      : "";
  }
}

async function loadProjectsPanel(force = false, selected = "", query = "") {
  if (!chatProjectsEl || (projectsLoaded && !force && !selected && !query)) return;
  const params = new URLSearchParams();
  if (selected) params.set("selected", selected);
  if (query) params.set("q", query);
  if (projectPreview && !projectsLoaded) projectPreview.innerHTML = '<div class="help-empty">Projekte werden geladen...</div>';
  try {
    const data = await fetchJson(`/api/projects${params.toString() ? `?${params}` : ""}`);
    renderProjectsPanel(data);
    projectsLoaded = true;
  } catch (error) {
    if (stateCache?.maat_project_memory?.projects) {
      renderProjectsPanel(stateCache.maat_project_memory);
      projectsLoaded = true;
    }
    if (projectPreview) projectPreview.innerHTML = `<div class="help-empty">Projektliste konnte nicht geladen werden: ${escapeHtml(error.message || error)}</div>`;
  }
}

function clearProjectChildInputs(kind = "all") {
  if (kind === "formula" || kind === "all") {
    if (projectFormulaName) projectFormulaName.value = "";
    if (projectFormulaDescription) projectFormulaDescription.value = "";
    if (projectFormulaText) projectFormulaText.value = "";
  }
  if (kind === "paper" || kind === "all") {
    if (projectPaperTitle) projectPaperTitle.value = "";
    if (projectPaperRef) projectPaperRef.value = "";
    if (projectPaperNotes) projectPaperNotes.value = "";
  }
  if (kind === "entry" || kind === "all") {
    if (projectEntryTags) projectEntryTags.value = "";
    if (projectEntryText) projectEntryText.value = "";
  }
}

function newProjectForm() {
  fillProjectForm(null);
  clearProjectChildInputs("all");
  if (projectSelect) projectSelect.value = "";
  if (projectPreview) projectPreview.innerHTML = renderMarkdown("## Neues Projekt\n\nTrage links die Daten ein und klicke auf **Projekt speichern**.");
  if (projectStatusText) projectStatusText.textContent = "Neue Projektmaske geöffnet";
}

async function saveProjectFromForm() {
  const payload = {
    id: projectName?.dataset.projectId || "",
    name: projectName?.value || "",
    version: projectVersion?.value || "",
    status: projectStatus?.value || "aktiv",
    tags: projectTags?.value || "",
    recall_triggers: projectTriggers?.value || "",
    description: projectDescription?.value || "",
    context: projectContext?.value || "",
  };
  try {
    const data = await fetchJson("/api/projects/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderProjectsPanel(data);
    if (projectStatusText) projectStatusText.textContent = data.ok ? `Gespeichert: ${data.project?.name || payload.name}` : data.error || "Fehler";
    projectsLoaded = true;
  } catch (error) {
    if (projectStatusText) projectStatusText.textContent = error.message || String(error);
  }
}

async function addProjectChild(kind) {
  const project = projectName?.dataset.projectId || projectName?.value || selectedProjectId();
  let payload = { kind, project };
  if (kind === "formula") {
    payload = {
      ...payload,
      name: projectFormulaName?.value || "",
      formula: projectFormulaText?.value || "",
      description: projectFormulaDescription?.value || "",
    };
  } else if (kind === "paper") {
    payload = {
      ...payload,
      title: projectPaperTitle?.value || "",
      ref: projectPaperRef?.value || "",
      notes: projectPaperNotes?.value || "",
    };
  } else {
    payload = {
      ...payload,
      entry_type: projectEntryType?.value || "insight",
      tags: projectEntryTags?.value || "",
      text: projectEntryText?.value || "",
    };
  }
  try {
    const data = await fetchJson("/api/projects/child", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderProjectsPanel(data);
    if (data.ok) clearProjectChildInputs(kind);
    if (projectStatusText) projectStatusText.textContent = data.ok ? "Gespeichert" : data.error || "Fehler";
  } catch (error) {
    if (projectStatusText) projectStatusText.textContent = error.message || String(error);
  }
}

function docsLang(filename = "") {
  const lower = String(filename || "").toLowerCase();
  if (lower.endsWith(".py")) return "python";
  if (lower.endsWith(".tex")) return "latex";
  if (lower.endsWith(".md")) return "markdown";
  if (lower.endsWith(".html") || lower.endsWith(".htm")) return "html";
  if (lower.endsWith(".json")) return "json";
  if (lower.endsWith(".csv")) return "csv";
  if (lower.endsWith(".pdf")) return "text";
  return "text";
}

function selectedDocId() {
  return docsSelect?.value || "";
}

function renderDocsPanel(data = {}) {
  stateCache = stateCache || {};
  stateCache.maat_file_builder = data;
  const settings = stateCache.settings || {};
  if (fileBuilderEnabled) fileBuilderEnabled.checked = settings.file_builder_enabled !== false;
  if (fileBuilderInject) fileBuilderInject.checked = settings.file_builder_inject_instructions !== false;
  if (fileBuilderReplace) fileBuilderReplace.checked = settings.file_builder_replace_blocks !== false;
  if (fileBuilderSource) fileBuilderSource.checked = settings.file_builder_show_source_code !== false;
  if (fileBuilderFences) fileBuilderFences.checked = settings.file_builder_auto_capture_fences !== false;
  if (fileBuilderCompileTex) fileBuilderCompileTex.checked = settings.file_builder_compile_tex_pdf !== false;
  if (fileBuilderPythonCheck) fileBuilderPythonCheck.checked = settings.file_builder_python_syntax_check !== false;
  if (fileBuilderPythonRun) fileBuilderPythonRun.checked = settings.file_builder_python_run_enabled !== false;
  if (fileBuilderTerminal) fileBuilderTerminal.checked = settings.file_builder_python_run_in_terminal !== false;
  if (fileBuilderFeedback) fileBuilderFeedback.checked = settings.file_builder_inject_feedback !== false;
  if (fileBuilderDebug) fileBuilderDebug.checked = Boolean(settings.file_builder_debug);
  if (fileBuilderPreviewChars) fileBuilderPreviewChars.value = settings.file_builder_preview_chars ?? data.preview_chars ?? 5000;
  if (docsRoot) docsRoot.textContent = data.root ? `Ordner: ${data.root}` : "";

  const records = data.records || [];
  const selected = data.selected || records[0] || null;
  const companionPdf = data.companion_pdf || null;
  const selectedIsPdf = Boolean(selected?.filename && String(selected.filename).toLowerCase().endsWith(".pdf"));
  if (docsSelect) {
    docsSelect.innerHTML = "";
    for (const record of records) {
      const option = document.createElement("option");
      option.value = record.id || "";
      option.textContent = `${record.filename || "Datei"} · ${formatChatDate(record.created_at || "")}`;
      option.title = record.relative_path || record.path || "";
      docsSelect.appendChild(option);
    }
    if (selected?.id) docsSelect.value = selected.id;
  }
  if (docsDownload) {
    if (selected?.id) {
      docsDownload.href = `/api/docs/download?id=${encodeURIComponent(selected.id)}`;
      docsDownload.removeAttribute("aria-disabled");
      docsDownload.classList.remove("disabled");
    } else {
      docsDownload.href = "#";
      docsDownload.setAttribute("aria-disabled", "true");
      docsDownload.classList.add("disabled");
    }
  }
  if (docsRunPython) {
    const isPython = Boolean(selected?.filename && String(selected.filename).toLowerCase().endsWith(".py"));
    docsRunPython.disabled = !isPython || settings.file_builder_python_run_enabled === false;
    docsRunPython.title = isPython ? "Diese Python-Datei lokal ausführen" : "Nur für .py-Dateien";
  }
  if (docsOpenFile) {
    const ext = selected?.filename ? String(selected.filename).split(".").pop().toUpperCase() : "Datei";
    docsOpenFile.disabled = !selected?.id;
    docsOpenFile.textContent = selected?.id ? `${ext} öffnen` : "Öffnen";
    docsOpenFile.title = selected?.id ? "Mit der Standard-App öffnen" : "Keine Datei ausgewählt";
  }
  if (docsPdfDownload) {
    if (companionPdf?.id && !selectedIsPdf) {
      docsPdfDownload.hidden = false;
      docsPdfDownload.href = `/api/docs/download?id=${encodeURIComponent(companionPdf.id)}`;
      docsPdfDownload.removeAttribute("aria-disabled");
      docsPdfDownload.classList.remove("disabled");
    } else {
      docsPdfDownload.hidden = true;
      docsPdfDownload.href = "#";
      docsPdfDownload.setAttribute("aria-disabled", "true");
      docsPdfDownload.classList.add("disabled");
    }
  }
  if (docsOpenPdf) {
    docsOpenPdf.hidden = !companionPdf?.id || selectedIsPdf;
    docsOpenPdf.disabled = !companionPdf?.id || selectedIsPdf;
    docsOpenPdf.textContent = companionPdf?.id ? "PDF öffnen" : "PDF öffnen";
  }
  if (docsDelete) {
    docsDelete.disabled = !selected?.id;
    docsDelete.title = selected?.id ? "Ausgewählte MAAT-Docs-Datei löschen" : "Keine Datei ausgewählt";
  }
  if (docsFilename && selected?.filename && !docsFilename.value) docsFilename.value = selected.filename;
  if (docsStatus) docsStatus.textContent = data.status || `${records.length} Dateien`;
  if (docsPreview) {
    const preview = data.preview || "";
    if (selected) {
      const title = `${selected.filename || "Datei"} · ${selected.relative_path || ""}`;
      docsPreview.innerHTML = `<h3>${escapeHtml(title)}</h3>${renderMarkdown(`\`\`\`${docsLang(selected.filename)}\n${preview}\n\`\`\``)}`;
    } else {
      docsPreview.innerHTML = '<div class="help-empty">Noch keine Datei vorhanden.</div>';
    }
  }
}

async function openDocId(id, label = "Datei", statusTarget = docsStatus) {
  if (!id) {
    if (statusTarget) statusTarget.textContent = "Keine Datei ausgewählt.";
    return;
  }
  try {
    const data = await fetchJson("/api/docs/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    renderDocsPanel(data);
    docsLoaded = true;
    if (statusTarget) statusTarget.textContent = data.ok ? `${label} geöffnet` : data.error || "Öffnen fehlgeschlagen.";
  } catch (error) {
    if (statusTarget) statusTarget.textContent = error.message || String(error);
  }
}

async function runPythonDocId(id, argsText = "", outputTarget = docsRunOutput, statusTarget = docsStatus) {
  if (!id) {
    if (outputTarget) outputTarget.textContent = "Keine Datei ausgewählt.";
    if (statusTarget) statusTarget.textContent = "Keine Datei ausgewählt.";
    return null;
  }
  if (outputTarget) outputTarget.textContent = "Python läuft...";
  try {
    const data = await fetchJson("/api/docs/run-python", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id,
        args: argsText || "",
        terminal: fileBuilderTerminal?.checked !== false,
      }),
    });
    renderDocsPanel(data);
    if (outputTarget) outputTarget.textContent = data.output || data.error || "Keine Ausgabe.";
    if (statusTarget) {
      statusTarget.textContent = data.terminal_started
        ? "Terminal gestartet"
        : data.ok
        ? `Python erfolgreich · exit ${data.returncode ?? 0}`
        : `Python Fehler · ${data.error || `exit ${data.returncode ?? "-"}`} · Log geht an KI`;
    }
    if (!data.ok) {
      addLogEntry({
        source: "docs",
        title: "Python-Ausführung fehlgeschlagen",
        lines: [
          data.error || `exit=${data.returncode ?? "-"}`,
          "Fehlerlog wird beim nächsten Turn still an die KI gegeben.",
        ],
      });
    }
    docsLoaded = true;
    return data;
  } catch (error) {
    if (outputTarget) outputTarget.textContent = error.message || String(error);
    if (statusTarget) statusTarget.textContent = error.message || String(error);
    return null;
  }
}

async function openSelectedDoc() {
  const selected = stateCache?.maat_file_builder?.selected || {};
  await openDocId(selectedDocId(), selected.filename || "Datei");
}

async function openSelectedPdf() {
  const companion = stateCache?.maat_file_builder?.companion_pdf || {};
  await openDocId(companion.id || "", companion.filename || "PDF");
}

async function loadDocsPanel(force = false, selected = "") {
  if (!chatDocsEl || (docsLoaded && !force && !selected)) return;
  if (docsPreview && !docsLoaded) docsPreview.innerHTML = '<div class="help-empty">Docs werden geladen...</div>';
  try {
    const params = new URLSearchParams();
    if (selected) params.set("selected", selected);
    const data = await fetchJson(`/api/docs${params.toString() ? `?${params}` : ""}`);
    renderDocsPanel(data);
    docsLoaded = true;
  } catch (error) {
    if (docsPreview) docsPreview.innerHTML = `<div class="help-empty">Docs konnten nicht geladen werden: ${escapeHtml(error.message || error)}</div>`;
  }
}

async function saveManualDoc() {
  const payload = {
    filename: docsFilename?.value || "maat_note.md",
    content: docsContent?.value || "",
  };
  try {
    const data = await fetchJson("/api/docs/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderDocsPanel(data);
    if (docsSaveStatus) docsSaveStatus.textContent = data.ok ? "Gespeichert" : data.error || "Fehler";
    if (data.ok && docsContent) docsContent.value = "";
    docsLoaded = true;
  } catch (error) {
    if (docsSaveStatus) docsSaveStatus.textContent = error.message || String(error);
  }
}

async function runSelectedPythonDoc() {
  const id = selectedDocId();
  if (!id) {
    if (docsRunOutput) docsRunOutput.textContent = "Keine Datei ausgewählt.";
    return;
  }
  await runPythonDocId(id, docsRunArgs?.value || "", docsRunOutput, docsStatus);
}

async function deleteSelectedDoc() {
  const id = selectedDocId();
  if (!id) {
    if (docsStatus) docsStatus.textContent = "Keine Datei ausgewählt.";
    return;
  }
  const selected = stateCache?.maat_file_builder?.selected || {};
  const name = selected.filename || "diese Datei";
  const confirmed = window.confirm(
    `Doc wirklich löschen?\n\n${name}\n\nGelöscht wird nur die verwaltete Datei im MAAT-Docs-Ordner.`
  );
  if (!confirmed) return;

  try {
    const data = await fetchJson("/api/docs/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    renderDocsPanel(data);
    docsLoaded = true;
    if (docsStatus) {
      docsStatus.textContent = data.ok
        ? `Gelöscht: ${data.deleted?.filename || name}`
        : data.error || "Löschen fehlgeschlagen.";
    }
    if (data.ok && docsRunOutput) docsRunOutput.textContent = "Noch kein Python-Lauf.";
  } catch (error) {
    if (docsStatus) docsStatus.textContent = error.message || String(error);
  }
}

function docExtension(record = {}) {
  const filename = String(record.filename || record.path || "");
  const suffix = String(record.extension || "").replace(/^\./, "");
  return (suffix || filename.split(".").pop() || "file").toLowerCase();
}

function renderFileBuilderChatCard(data = {}) {
  const records = Array.isArray(data.records) ? data.records : [];
  const errors = Array.isArray(data.errors) ? data.errors : [];
  if (!records.length && !errors.length) return "";

  const rows = records
    .map((record) => {
      const id = escapeHtml(record.id || "");
      const filename = escapeHtml(record.filename || "Datei");
      const ext = docExtension(record);
      const label = ext === "pdf" ? "PDF" : ext === "tex" ? "LaTeX" : ext === "py" ? "Python" : ext.toUpperCase();
      const size = formatBytes(Number(record.bytes || 0));
      const relativePath = escapeHtml(record.relative_path || "");
      const downloadUrl = `/api/docs/download?id=${encodeURIComponent(record.id || "")}`;
      const isPython = ext === "py";
      const downloadLabel =
        ext === "pdf" ? "PDF Download" : ext === "tex" ? "TEX Download" : ext === "py" ? "PY Download" : "Download";
      const openLabel = ext === "pdf" ? "PDF öffnen" : ext === "tex" ? "TEX öffnen" : ext === "py" ? "PY öffnen" : "Öffnen";
      return (
        `<div class="file-builder-row" data-doc-id="${id}">` +
        `<div class="file-builder-main">` +
        `<strong>${filename}</strong>` +
        `<small>${escapeHtml(label)}${size ? ` · ${escapeHtml(size)}` : ""}${relativePath ? ` · ${relativePath}` : ""}</small>` +
        `</div>` +
        `<div class="file-builder-actions">` +
        `<a class="mini-button docs-download" href="${escapeHtml(downloadUrl)}" download>${escapeHtml(downloadLabel)}</a>` +
        `<button class="mini-button" type="button" data-doc-open="${id}">${escapeHtml(openLabel)}</button>` +
        (isPython ? `<button class="mini-button" type="button" data-doc-run="${id}">PY ausführen</button>` : "") +
        `</div>` +
        `<div class="file-builder-status" aria-live="polite"></div>` +
        `</div>`
      );
    })
    .join("");

  const errorHtml = errors
    .map((error) => `<div class="file-builder-error">${escapeHtml(error)}</div>`)
    .join("");

  const title = records.length === 1 ? "📄 Datei angelegt" : `📄 ${records.length} Dateien angelegt`;
  return (
    `<div class="message-file-builder-card">` +
    `<div class="file-builder-card-title">${escapeHtml(title)}</div>` +
    `${rows}` +
    `${errorHtml}` +
    `</div>`
  );
}

function attachFileBuilderCardHandlers(container) {
  container.querySelectorAll("[data-doc-open]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const row = button.closest(".file-builder-row");
      const status = row?.querySelector(".file-builder-status") || null;
      const filename = row?.querySelector("strong")?.textContent || "Datei";
      button.disabled = true;
      if (status) status.textContent = "öffnet...";
      await openDocId(button.dataset.docOpen || "", filename, status);
      button.disabled = false;
    });
  });

  container.querySelectorAll("[data-doc-run]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const row = button.closest(".file-builder-row");
      const status = row?.querySelector(".file-builder-status") || null;
      button.disabled = true;
      if (status) status.textContent = "startet...";
      await runPythonDocId(button.dataset.docRun || "", "", status, status);
      button.disabled = false;
    });
  });
}

function appendFileBuilderChatCard(messageElement, data = {}) {
  if (!messageElement) return;
  const html = renderFileBuilderChatCard(data);
  if (!html) return;
  const content = messageElement.querySelector(".message-content") || messageElement;
  content.querySelectorAll(".message-file-builder-card").forEach((card) => card.remove());
  content.insertAdjacentHTML("beforeend", html);
  attachFileBuilderCardHandlers(content);
}

function clearChatLog(message = "Noch keine Log-Einträge in dieser Sitzung.") {
  if (!chatLogEl) return;
  chatLogEl.innerHTML = `<div class="log-empty">${escapeHtml(message)}</div>`;
}

function logLineText(item) {
  if (!item || typeof item !== "object") return "";
  const parts = [];
  if (item.index) parts.push(`${item.index}.`);
  if (item.source) parts.push(`[${item.source}]`);
  if (Number.isFinite(item.score)) parts.push(`score=${item.score.toFixed(2)}`);
  const meta = [item.category, item.memory_type, item.maat_field].filter(Boolean).join("/");
  if (meta) parts.push(meta);
  if (item.author_user) parts.push(`author=${item.author_user}`);
  if (item.content) parts.push(`- ${item.content}`);
  return parts.join(" ");
}

function addLogEntry(payload = {}) {
  if (!chatLogEl) return;
  const empty = chatLogEl.querySelector(".log-empty");
  empty?.remove();

  const entry = document.createElement("div");
  entry.className = `log-entry ${payload.source ? `log-${String(payload.source).replace(/[^a-z0-9_-]/gi, "").toLowerCase()}` : ""}`;

  const head = document.createElement("div");
  head.className = "log-entry-head";
  const title = document.createElement("strong");
  title.textContent = payload.title || "Log";
  const time = document.createElement("span");
  time.textContent = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  head.append(title, time);
  entry.appendChild(head);

  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  const itemLines = Array.isArray(payload.items) ? payload.items.map(logLineText).filter(Boolean) : [];
  const contentLines = [...lines, ...itemLines];
  if (payload.content) contentLines.push(String(payload.content));
  if (contentLines.length) {
    const pre = document.createElement("pre");
    pre.textContent = contentLines.join("\n");
    entry.appendChild(pre);
  }

  chatLogEl.appendChild(entry);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

const saveStatusTimers = new WeakMap();

function flashSavedStatus(element, text = "Gespeichert") {
  if (!element) return;
  const oldTimer = saveStatusTimers.get(element);
  if (oldTimer) clearTimeout(oldTimer);
  element.textContent = text;
  element.classList.add("visible");
  const timer = setTimeout(() => {
    element.classList.remove("visible");
  }, 1800);
  saveStatusTimers.set(element, timer);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const raw = await response.text();
  const preview = raw.trim().slice(0, 120);

  if (!response.ok) {
    if (preview.startsWith("<!DOCTYPE") || preview.startsWith("<html")) {
      throw new Error(`Backend liefert HTML statt JSON für ${url}. Bitte Web-Core komplett neu starten, damit die neue API-Route aktiv ist.`);
    }
    throw new Error(`HTTP ${response.status}: ${preview || response.statusText}`);
  }

  if (!contentType.includes("application/json")) {
    if (preview.startsWith("<!DOCTYPE") || preview.startsWith("<html")) {
      throw new Error(`Backend liefert HTML statt JSON für ${url}. Bitte Web-Core komplett neu starten, damit die neue API-Route aktiv ist.`);
    }
    throw new Error(`Antwort ist kein JSON (${contentType || "unbekannter Inhaltstyp"}): ${preview || "leer"}`);
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`JSON konnte nicht gelesen werden: ${error.message}`);
  }
}

function textByteLength(value) {
  return new Blob([String(value ?? "")]).size;
}

function makeAttachmentId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `att-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseAttachmentAttributes(value) {
  const attrs = {};
  const regex = /([a-z0-9_-]+)="([^"]*)"/gi;
  let match;
  while ((match = regex.exec(String(value || ""))) !== null) {
    attrs[match[1]] = match[2];
  }
  return attrs;
}

function attachmentHeader(attachment) {
  const name = String(attachment.name || "Eingefügter Text.txt").replace(/"/g, "'");
  const type = String(attachment.type || "text/plain").replace(/"/g, "'");
  const chars = String(attachment.content || "").length;
  const bytes = textByteLength(attachment.content || "");
  return `[MAAT_ATTACHMENT name="${name}" type="${type}" chars="${chars}" bytes="${bytes}"]`;
}

function attachmentBlock(attachment) {
  return `${attachmentHeader(attachment)}\n${attachment.content || ""}\n[/MAAT_ATTACHMENT]`;
}

function parseAttachmentsFromText(raw) {
  const source = String(raw ?? "");
  const attachments = [];
  const regex = /\[MAAT_ATTACHMENT([^\]]*)\]\n?([\s\S]*?)\n?\[\/MAAT_ATTACHMENT\]/gi;
  let cleanText = "";
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(source)) !== null) {
    cleanText += source.slice(lastIndex, match.index);
    const attrs = parseAttachmentAttributes(match[1]);
    const content = match[2] || "";
    attachments.push({
      id: makeAttachmentId(),
      name: attrs.name || `Eingefügter Text ${attachments.length + 1}.txt`,
      type: attrs.type || "text/plain",
      chars: Number(attrs.chars) || content.length,
      bytes: Number(attrs.bytes) || textByteLength(content),
      content,
    });
    cleanText += `\n[Anhang: ${attrs.name || "Eingefügter Text.txt"}]\n`;
    lastIndex = regex.lastIndex;
  }

  cleanText += source.slice(lastIndex);
  return { cleanText, attachments };
}

function stripAttachmentBlocks(raw) {
  const { cleanText } = parseAttachmentsFromText(raw);
  return cleanText;
}

function renderAttachmentCard(attachment, pending = false) {
  const content = String(attachment.content || "");
  const chars = Number(attachment.chars) || content.length;
  const bytes = Number(attachment.bytes) || textByteLength(content);
  const preview = content.replace(/\s+/g, " ").trim().slice(0, 260);
  const meta = `${chars.toLocaleString("de-DE")} Zeichen · ${formatBytes(bytes)}`;
  const removeButton = pending
    ? `<button class="attachment-remove" type="button" data-attachment-id="${escapeHtml(attachment.id)}" title="Anhang entfernen">×</button>`
    : "";

  return (
    `<details class="attachment-card"${pending ? " open" : ""}>` +
    `<summary>` +
    `<span class="attachment-icon">📎</span>` +
    `<span class="attachment-main"><strong>${escapeHtml(attachment.name || "Eingefügter Text.txt")}</strong><small>${escapeHtml(meta)}</small></span>` +
    `${removeButton}` +
    `</summary>` +
    `<div class="attachment-preview">${escapeHtml(preview || "Textanhang")}</div>` +
    `<pre>${escapeHtml(content)}</pre>` +
    `</details>`
  );
}

function renderMessageWithAttachments(raw) {
  const { cleanText, attachments } = parseAttachmentsFromText(raw);
  const html = [];
  const text = cleanText.replace(/\n\s*\[Anhang:[^\]]+\]\s*\n/g, "\n\n").trim();
  if (text) html.push(renderMarkdown(text));
  if (attachments.length) {
    html.push(`<div class="message-attachments">${attachments.map((item) => renderAttachmentCard(item)).join("")}</div>`);
  }
  return html.join("") || "";
}

function shouldCreatePasteAttachment(text) {
  const value = String(text || "");
  if (!value.trim()) return false;
  const lineCount = value.split(/\r\n|\r|\n/).length;
  return value.length >= PASTE_ATTACHMENT_THRESHOLD || lineCount >= PASTE_ATTACHMENT_MIN_LINES;
}

function nextAttachmentName() {
  const index = pendingAttachments.length + 1;
  return index === 1 ? "Eingefügter Text.txt" : `Eingefügter Text ${index}.txt`;
}

function addPendingTextAttachment(text) {
  const content = String(text || "").replace(/\r\n/g, "\n");
  pendingAttachments.push({
    id: makeAttachmentId(),
    name: nextAttachmentName(),
    type: "text/plain",
    content,
    chars: content.length,
    bytes: textByteLength(content),
  });
  renderAttachmentTray();
}

function renderAttachmentTray() {
  if (!attachmentTray) return;
  if (!pendingAttachments.length) {
    attachmentTray.hidden = true;
    attachmentTray.innerHTML = "";
    return;
  }
  attachmentTray.hidden = false;
  attachmentTray.innerHTML = pendingAttachments.map((item) => renderAttachmentCard(item, true)).join("");
  attachmentTray.querySelectorAll(".attachment-remove").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const id = button.dataset.attachmentId;
      pendingAttachments = pendingAttachments.filter((item) => item.id !== id);
      renderAttachmentTray();
    });
  });
}

function clearPendingAttachments() {
  pendingAttachments = [];
  renderAttachmentTray();
}

function buildOutgoingMessage(typedText) {
  const blocks = pendingAttachments.map(attachmentBlock);
  return [String(typedText || "").trim(), ...blocks].filter(Boolean).join("\n\n");
}

function createRenderToken(tokens, html) {
  const token = `@@MAATRENDERTOKEN${tokens.length}@@`;
  tokens.push({ token, html });
  return token;
}

function renderCopyableBlock(kind, label, copyValue, innerHtml) {
  return (
    `<div class="copyable-block ${escapeHtml(kind)}" data-copy="${escapeHtml(copyValue)}">` +
    `<div class="block-copy-bar"><span>${escapeHtml(label)}</span>` +
    `<button class="block-copy-button" type="button" title="${escapeHtml(label)} kopieren">Copy</button></div>` +
    innerHtml +
    `</div>`
  );
}

function isMaatDebugBlock(value) {
  const text = String(value ?? "").trim();
  return (
    /\bH\s*=\s*\d+(?:\.\d+)?\s+B\s*=\s*\d+(?:\.\d+)?\s+S\s*=\s*\d+(?:\.\d+)?\s+V\s*=\s*\d+(?:\.\d+)?\s+R\s*=\s*\d+(?:\.\d+)?/i.test(text) &&
    /\bStability\s*=/i.test(text) &&
    /\bMaat Value\s*=|\bFokusfelder\s*:/i.test(text)
  );
}

function collapseLeadingMaatScoreBlocks(value) {
  const text = String(value ?? "");
  let pos = 0;
  const blocks = [];
  while (pos < text.length) {
    const rest = text.slice(pos);
    const opening = /^\s*```(?:text)?[ \t]*\n/i.exec(rest);
    if (!opening) break;
    const bodyStart = pos + opening[0].length;
    const closing = /^```[ \t]*$/m.exec(text.slice(bodyStart));
    if (!closing) break;
    const bodyEnd = bodyStart + closing.index;
    const blockEnd = bodyStart + closing.index + closing[0].length;
    const body = text.slice(bodyStart, bodyEnd);
    if (!isMaatDebugBlock(body)) break;
    blocks.push(text.slice(pos, blockEnd).trim());
    pos = blockEnd;
  }
  if (blocks.length <= 1) return text;
  return `${blocks[0]}\n\n${text.slice(pos).trimStart()}`.trim();
}

function renderMaatDebugBlock(value) {
  const lines = String(value ?? "")
    .trim()
    .split(/\r?\n/)
    .map((line) => `<div>${escapeHtml(line)}</div>`)
    .join("");
  return `<div class="maat-chat-debug">${lines}</div>`;
}

function renderMathSource(source, displayMode = false) {
  const formula = String(source ?? "").trim();
  const tag = displayMode ? "div" : "span";
  const klass = displayMode ? "math-block" : "math-inline";
  if (!formula) return "";

  if (window.katex?.renderToString) {
    try {
      const rendered = window.katex.renderToString(formula, {
        displayMode,
        throwOnError: false,
        strict: "ignore",
        trust: false,
        output: "htmlAndMathml",
      });
      return displayMode ? renderCopyableBlock("math-copy-block", "Formel", formula, rendered) : rendered;
    } catch (error) {
      console.warn("KaTeX render failed", error);
    }
  }

  const fallback = `<${tag} class="${klass}">${escapeHtml(formula)}</${tag}>`;
  return displayMode ? renderCopyableBlock("math-copy-block", "Formel", formula, fallback) : fallback;
}

function restoreRenderTokens(html, tokens) {
  let restored = html;
  for (const item of tokens) {
    restored = restored.replaceAll(item.token, item.html);
  }
  return restored;
}

function cleanVisibleText(value) {
  return String(value ?? "")
    .replace(/<details\b[^>]*class=["'][^"']*\bmaat-memory-save-box\b[^"']*["'][^>]*>[\s\S]*?<\/details>\s*/gi, "")
    .replace(/\[MAAT_DOCS_CARD\][\s\S]*?\[\/MAAT_DOCS_CARD\]\s*/gi, "")
    .replace(/\[MAAT_CLAIM_GUARD\][\s\S]*?\[\/MAAT_CLAIM_GUARD\]\s*/gi, "")
    .replace(/\[\/?MAAT_CLAIM_GUARD\]\s*/gi, "")
    .replace(/<\|channel>thought[\s\S]*?<channel\|>\s*/gi, "")
    .replace(/<\|channel>thought[\s\S]*/gi, "")
    .replace(/<\|\/?(?:turn|channel|think|bos|eos)[^>]*\|?>/gi, "")
    .replace(/<(?:turn|channel)\|>/gi, "")
    .replace(/<\/?(?:bos|eos)>/gi, "")
    .replace(/@@MAAT_?RENDER_?TOKEN_?\d+@@/gi, "");
}

function visibleCopyText(raw, role) {
  if (role === "assistant") {
    return collapseLeadingMaatScoreBlocks(cleanVisibleText(splitThinking(raw).answer)).trim();
  }
  return cleanVisibleText(raw).trim();
}

function stripMaatDebugForSpeech(value) {
  let text = String(value ?? "");
  text = text.replace(
    /```(?:text)?\s*H=\d+(?:\.\d+)?\s+B=\d+(?:\.\d+)?\s+S=\d+(?:\.\d+)?\s+V=\d+(?:\.\d+)?\s+R=\d+(?:\.\d+)?[\s\S]*?```/gi,
    " ",
  );
  text = text.replace(
    /^\s*H=\d+(?:\.\d+)?\s+B=\d+(?:\.\d+)?\s+S=\d+(?:\.\d+)?\s+V=\d+(?:\.\d+)?\s+R=\d+(?:\.\d+)?\s+→\s+Stability=\d+(?:\.\d+)?\s*$/gim,
    "",
  );
  text = text.replace(/^\s*Maat Value=\d+(?:\.\d+)?\s*$/gim, "");
  text = text.replace(/^\s*Fokusfelder:.*$/gim, "");
  text = text.replace(/^\s*B_dynamic=.*$/gim, "");
  text = text.replace(/^\s*CCI(?:_runtime)?=.*$/gim, "");
  text = text.replace(/```[\s\S]*?```/g, " ");
  return text.replace(/\n{3,}/g, "\n\n").trim();
}

function visibleSpeakText(raw, role) {
  return stripMaatDebugForSpeech(visibleCopyText(raw, role));
}

function decodeHtmlEntities(value) {
  const area = document.createElement("textarea");
  area.innerHTML = String(value ?? "");
  return area.value;
}

function splitMemorySaveBoxes(raw) {
  const boxes = [];
  const clean = String(raw ?? "").replace(
    /<details\b[^>]*class=["'][^"']*\bmaat-memory-save-box\b[^"']*["'][^>]*>([\s\S]*?)<\/details>/gi,
    (_match, body) => {
      const summaryMatch = /<summary[^>]*>([\s\S]*?)<\/summary>/i.exec(body);
      const codeMatch = /<pre[^>]*>\s*<code[^>]*>([\s\S]*?)<\/code>\s*<\/pre>/i.exec(body);
      const fallbackCode = body.replace(/<summary[^>]*>[\s\S]*?<\/summary>/i, "").replace(/<[^>]+>/g, "").trim();
      boxes.push({
        summary: decodeHtmlEntities(summaryMatch?.[1] || "🧠 Erinnerung angelegt — mehr anzeigen"),
        code: decodeHtmlEntities(codeMatch?.[1] || fallbackCode),
      });
      return "\n\n";
    },
  );
  return { clean, boxes };
}

function renderMemorySaveBox(box = {}) {
  const summary = String(box.summary || "🧠 Erinnerung angelegt — mehr anzeigen").trim();
  const code = String(box.code || "").trim();
  return (
    `<details class="maat-memory-save-box">` +
    `<summary>${escapeHtml(summary)}</summary>` +
    `<pre><code>${escapeHtml(code || "save: (...)")}</code></pre>` +
    `</details>`
  );
}

async function copyText(text) {
  const value = String(text ?? "");
  if (!value) return false;
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // Fallback below.
    }
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  area.remove();
  return ok;
}

function attachCopyableBlockButtons(container) {
  container.querySelectorAll(".block-copy-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const block = button.closest(".copyable-block");
      const ok = await copyText(block?.dataset?.copy || "");
      button.textContent = ok ? "Kopiert" : "Fehler";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1200);
    });
  });
}

function resetSpeakButton(button = activeSpeakButton) {
  if (!button) return;
  button.textContent = "Vorlesen";
  button.classList.remove("active");
  button.title = "Nachricht vorlesen";
  if (button === activeSpeakButton) {
    activeSpeakButton = null;
    activeSpeechMode = null;
  }
}

function preferredBrowserVoice() {
  if (!window.speechSynthesis?.getVoices) return null;
  const voices = window.speechSynthesis.getVoices() || [];
  return (
    voices.find((voice) => /^de[-_]/i.test(voice.lang || "") && /anna|siri|premium|german|deutsch/i.test(voice.name || "")) ||
    voices.find((voice) => /^de[-_]/i.test(voice.lang || "")) ||
    null
  );
}

function speakWithBrowser(value) {
  if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
    return { ok: false, error: "Browser-Sprachausgabe nicht verfügbar." };
  }
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(value);
    utterance.lang = "de-DE";
    utterance.rate = 1;
    utterance.pitch = 1;
    const voice = preferredBrowserVoice();
    if (voice) utterance.voice = voice;
    utterance.onend = () => resetSpeakButton();
    utterance.onerror = () => resetSpeakButton();
    window.speechSynthesis.speak(utterance);
    window.setTimeout(() => {
      try {
        window.speechSynthesis.resume();
      } catch {
        // Some browsers do not need or support resume here.
      }
    }, 80);
    return { ok: true, status: "browser-speaking" };
  } catch (error) {
    return { ok: false, error: String(error.message || error) };
  }
}

async function stopSpeaking() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  try {
    await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "stop" }),
    });
  } catch {
    // Backend may be unavailable; browser fallback was already cancelled above.
  }
  resetSpeakButton();
  return { ok: true, status: "stopped" };
}

async function speakText(text) {
  const value = String(text ?? "").trim();
  if (!value) return { ok: false, error: "Kein Text" };
  const browserResult = speakWithBrowser(value);
  if (browserResult.ok) {
    activeSpeechMode = "browser";
    return browserResult;
  }
  try {
    const response = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: value }),
    });
    const result = await response.json();
    if (result?.ok) activeSpeechMode = "server";
    return result;
  } catch (error) {
    return { ok: false, error: String(error.message || error || browserResult.error) };
  }
}

function renderInlineMarkdown(value) {
  const tokens = [];
  let source = String(value ?? "");

  source = source.replace(/`([^`]+)`/g, (_, code) => {
    return createRenderToken(tokens, `<code>${escapeHtml(code)}</code>`);
  });

  source = source.replace(/\\\(([\s\S]+?)\\\)/g, (_, formula) => {
    return createRenderToken(tokens, renderMathSource(formula, false));
  });
  source = source.replace(/\$(?!\$)([^$\n]+)\$/g, (_, formula) => {
    return createRenderToken(tokens, renderMathSource(formula, false));
  });

  let html = escapeHtml(source);
  html = html.replace(/\*\*([^*\n]+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__([^_\n]+?)__/g, "<strong>$1</strong>");
  html = html.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  html = html.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, "$1<em>$2</em>");

  return restoreRenderTokens(html, tokens);
}

function renderMarkdown(value) {
  const lines = collapseLeadingMaatScoreBlocks(cleanVisibleText(value)).replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];

  function flushParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${renderInlineMarkdown(paragraph.join("\n")).replace(/\n/g, "<br>")}</p>`);
    paragraph = [];
  }

  function isBuilderUiArtifactLine(line) {
    return /^\s*(copy|vorlesen|denken anzeigen|py download|py öffnen|py ausführen|tex download|tex öffnen|pdf download|pdf öffnen|terminal gestartet|python syntax-check fehlgeschlagen\.?|📄\s*(datei( angelegt)?|docs? angelegt|[0-9]+\s+dateien angelegt).*|(python|latex|tex|html|markdown|text|json|csv|pdf)\s*·\s*[^/]+\/.*)\s*$/i.test(
      String(line ?? ""),
    );
  }

  function isRawCodeLabel(line) {
    return /^\s*code\s*(?:[·:\-]\s*)?(python|py|javascript|js|html|css|json|latex|tex|markdown|md|text|txt)?\s*$/i.test(
      String(line ?? ""),
    );
  }

  function isRawCodeStop(line) {
    return /^\s*(starte\s+mit\b|neu:|sag bescheid\b|ein konkreter anker\b|📄\s*(datei|[0-9]+\s+dateien)|py download|py öffnen|py ausführen)\b/i.test(
      String(line ?? ""),
    );
  }

  function languageFromRawCodeLabel(line) {
    const match = /^\s*code\s*(?:[·:\-]\s*)?([A-Za-z0-9_-]+)?\s*$/i.exec(String(line ?? ""));
    const raw = (match?.[1] || "text").toLowerCase();
    if (raw === "py") return "python";
    if (raw === "md") return "markdown";
    if (raw === "tex") return "latex";
    if (raw === "txt") return "text";
    return raw || "text";
  }

  function looksLikeCodeLine(line) {
    return /^\s*(import\s+\w+|from\s+\w+\s+import\b|class\s+\w+|def\s+\w+\(|if\s+__name__|while\s+|for\s+|elif\s+|else:|try:|except\b|with\s+|return\b|self\.|\w+\s*=|#|\}|\]|<\/?\w+)/.test(
      String(line ?? ""),
    );
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      continue;
    }

    if (trimmed.startsWith("```")) {
      flushParagraph();
      const lang = escapeHtml(trimmed.slice(3).trim());
      const code = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      const rawCode = code.join("\n");
      if (isMaatDebugBlock(rawCode)) {
        html.push(renderMaatDebugBlock(rawCode));
        continue;
      }
      html.push(
        renderCopyableBlock(
          "code-copy-block",
          lang ? `Code · ${trimmed.slice(3).trim()}` : "Code",
          rawCode,
          `<pre class="code-block"${lang ? ` data-lang="${lang}"` : ""}><code>${escapeHtml(rawCode)}</code></pre>`,
        ),
      );
      continue;
    }

    if (isRawCodeLabel(line)) {
      flushParagraph();
      const lang = languageFromRawCodeLabel(line);
      const code = [];
      index += 1;
      while (index < lines.length && /^\s*(copy|kopieren)\s*$/i.test(lines[index])) index += 1;
      while (index < lines.length) {
        const current = lines[index];
        if (isRawCodeStop(current)) break;
        if (isRawCodeLabel(current)) break;
        if (isBuilderUiArtifactLine(current)) {
          index += 1;
          continue;
        }
        code.push(current);
        index += 1;
      }
      index -= 1;
      const rawCode = code.join("\n").trim();
      const hasCode = rawCode.split("\n").filter((item) => item.trim()).some(looksLikeCodeLine);
      if (hasCode) {
        html.push(
          renderCopyableBlock(
            "code-copy-block",
            `Code · ${lang}`,
            rawCode,
            `<pre class="code-block" data-lang="${escapeHtml(lang)}"><code>${escapeHtml(rawCode)}</code></pre>`,
          ),
        );
      }
      continue;
    }

    if (trimmed === "$$" || trimmed.startsWith("$$")) {
      flushParagraph();
      const formula = [];
      const first = trimmed.slice(2).trim();
      if (first && !first.endsWith("$$")) formula.push(first);
      if (first.endsWith("$$")) {
        formula.push(first.slice(0, -2).trim());
      } else {
        index += 1;
        while (index < lines.length && !lines[index].trim().endsWith("$$")) {
          formula.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) {
          formula.push(lines[index].trim().replace(/\$\$$/, "").trim());
        }
      }
      html.push(renderMathSource(formula.join("\n"), true));
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      flushParagraph();
      const level = Math.min(heading[1].length + 2, 6);
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    if (/^([-*_])\1\1+$/.test(trimmed)) {
      flushParagraph();
      html.push("<hr>");
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      flushParagraph();
      const items = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*]\s+/, ""));
        index += 1;
      }
      index -= 1;
      html.push(`<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`);
      continue;
    }

    if (/^\s*\d+[.)]\s+/.test(line)) {
      flushParagraph();
      const items = [];
      while (index < lines.length && /^\s*\d+[.)]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+[.)]\s+/, ""));
        index += 1;
      }
      index -= 1;
      html.push(`<ol>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ol>`);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      flushParagraph();
      const quotes = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quotes.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      index -= 1;
      html.push(`<blockquote>${renderInlineMarkdown(quotes.join("\n")).replace(/\n/g, "<br>")}</blockquote>`);
      continue;
    }

    paragraph.push(line);
  }
  flushParagraph();
  return html.join("");
}

function freeThinkingStarts(text) {
  return /^\s*(here(?:'|’)?s a thinking process:|thinking process:|analy[sz]e user input:|denkprozess:|gedankenprozess:|the user\b|user said:|the prompt\b|the system instructions\b|i need to\b|we need to\b|apply maat principles:)/i.test(
    text,
  );
}

function internalThinkingHints(text) {
  return /(self[- ]correction|refinement during|output generation|proceeds?\.?|all constraints met|no internal tags visible|draft(?:ing)?|plan:|response plan|i'?ll\s+(?:keep|use|answer|write|provide|create)|the prompt says|matches the final response|ready\.?\s*$)/im.test(
    String(text ?? ""),
  );
}

function findFinalAnswerStart(text) {
  const marker =
    /^\s*(\[(antwort|final|final answer|output)\]|(final output generation|final output|final answer|antwort|output)\s*:)\s*/im.exec(
      text,
    );
  if (marker && marker.index > 24 && marker.index + marker[0].length < text.length) {
    return marker.index + marker[0].length;
  }

  const answerRegex =
    /^\s*(gern geschehen[!,.]?|gern[!,.]?|gerne[!,.]?|sehr gern[!,.]?|kein problem[!,.]?|hallo\b|hi\b|hey\b|klar[!,.]?|alles klar[!,.]?|natürlich[!,.]?|ja[!,.]?|nein[!,.]?|gut[!,.]?|passt[!,.]?|fertig[!,.]?|hier\b|hier\s+(?:ist|kommt|die|der|das)\b|das\s+(?:ist|passt|geht|klingt)\b|ich\s+(?:habe|würde|sehe|denke)\b|die wohl bekannteste\b|die bekannteste\b|die formel\b|einstein\b)/gim;
  let match;
  while ((match = answerRegex.exec(text)) !== null) {
    const start = match.index + match[0].length - match[1].length;
    if (start > 24) return start;
  }
  return -1;
}

function splitThinking(raw) {
  const text = String(raw ?? "");
  const lower = text.toLowerCase();
  const ranges = [];

  function addRange(start, end, complete = true) {
    const safeStart = Math.max(0, Math.min(start, text.length));
    const safeEnd = Math.max(safeStart, Math.min(end, text.length));
    if (safeEnd > safeStart) ranges.push({ start: safeStart, end: safeEnd, complete });
  }

  const firstClose = lower.indexOf("</think>");
  const firstOpen = lower.indexOf("<think>");
  if (firstClose >= 0 && (firstOpen < 0 || firstClose < firstOpen)) {
    addRange(0, firstClose + "</think>".length, true);
  }

  const gemmaThoughtRegex = /<\|channel>thought/gi;
  let gemmaThoughtMatch;
  while ((gemmaThoughtMatch = gemmaThoughtRegex.exec(text)) !== null) {
    const start = gemmaThoughtMatch.index;
    const contentStart = start + gemmaThoughtMatch[0].length;
    const close = lower.indexOf("<channel|>", contentStart);
    if (close < 0) {
      addRange(start, text.length, false);
      break;
    }
    addRange(start, close + "<channel|>".length, true);
    gemmaThoughtRegex.lastIndex = close + "<channel|>".length;
  }

  const freeBlockRegex =
    /(here(?:'|’)?s a thinking process:|thinking process:|analy[sz]e user input:|denkprozess:|gedankenprozess:|the user\b|user said:|the prompt\b|the system instructions\b|i need to\b|we need to\b|apply maat principles:)[\s\S]*?<\/think>/gi;
  let freeBlockMatch;
  while ((freeBlockMatch = freeBlockRegex.exec(text)) !== null) {
    addRange(freeBlockMatch.index, freeBlockMatch.index + freeBlockMatch[0].length, true);
  }

  const openRegex = /<think>/gi;
  let openMatch;
  while ((openMatch = openRegex.exec(text)) !== null) {
    const start = openMatch.index;
    const contentStart = start + openMatch[0].length;
    const close = lower.indexOf("</think>", contentStart);
    if (close < 0) {
      addRange(start, text.length, false);
      break;
    }
    addRange(start, close + "</think>".length, true);
    openRegex.lastIndex = close + "</think>".length;
  }

  const bracketOpenRegex = /\[(denken|thinking|gedanken)\]/gi;
  let bracketMatch;
  while ((bracketMatch = bracketOpenRegex.exec(text)) !== null) {
    const tag = bracketMatch[1];
    const start = bracketMatch.index;
    const contentStart = start + bracketMatch[0].length;
    const closeRegex = new RegExp(`\\[\\/${tag}\\]`, "i");
    const closeMatch = closeRegex.exec(text.slice(contentStart));
    if (!closeMatch) {
      addRange(start, text.length, false);
      break;
    }
    addRange(start, contentStart + closeMatch.index + closeMatch[0].length, true);
    bracketOpenRegex.lastIndex = contentStart + closeMatch.index + closeMatch[0].length;
  }

  if (
    ranges.length === 0 &&
    (freeThinkingStarts(text) || internalThinkingHints(text.slice(0, Math.max(0, findFinalAnswerStart(text)))))
  ) {
    const answerStart = findFinalAnswerStart(text);
    addRange(0, answerStart > 0 ? answerStart : text.length, answerStart > 0);
  }

  if (ranges.length > 0) {
    const sortedRanges = [...ranges].sort((a, b) => a.start - b.start);
    const lastRange = sortedRanges[sortedRanges.length - 1];
    const tail = text.slice(lastRange.end);
    const leadingWhitespace = /^\s*/.exec(tail)?.[0]?.length || 0;
    const tailStart = lastRange.end + leadingWhitespace;
    const tailText = text.slice(tailStart);
    if (tailText && freeThinkingStarts(tailText)) {
      const close = tailText.toLowerCase().indexOf("</think>");
      const answerStart = findFinalAnswerStart(tailText);
      if (close >= 0 && (answerStart < 0 || close < answerStart)) {
        addRange(tailStart, tailStart + close + "</think>".length, true);
      } else {
        addRange(tailStart, answerStart > 0 ? tailStart + answerStart : text.length, answerStart > 0);
      }
    }
  }

  if (!ranges.length) return { answer: text, thoughts: [] };

  ranges.sort((a, b) => a.start - b.start);
  const merged = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (last && range.start <= last.end) {
      last.end = Math.max(last.end, range.end);
      last.complete = last.complete && range.complete;
    } else {
      merged.push({ ...range });
    }
  }

  const thoughts = [];
  let answer = "";
  let position = 0;
  for (const range of merged) {
    answer += text.slice(position, range.start);
    const content = text
      .slice(range.start, range.end)
      .replace(/<\/?think>/gi, "")
      .replace(/\[(\/?)(denken|thinking|gedanken)\]/gi, "")
      .replace(/<\|channel>thought/gi, "")
      .replace(/<channel\|>/gi, "")
      .replace(/<\|\/?(?:turn|channel|think|bos|eos)[^>]*\|?>/gi, "")
      .replace(/<(?:turn|channel)\|>/gi, "")
      .replace(/<\/?(?:bos|eos)>/gi, "")
      .trim();
    if (content) thoughts.push({ content, complete: range.complete });
    position = range.end;
  }
  answer += text.slice(position);
  return { answer, thoughts };
}

function thinkingEnabled() {
  return Boolean(stateCache?.settings?.enable_thinking);
}

function splitDocsCards(raw) {
  const cards = [];
  const clean = String(raw ?? "").replace(
    /\[MAAT_DOCS_CARD\]([\s\S]*?)\[\/MAAT_DOCS_CARD\]/gi,
    (_match, body) => {
      try {
        const payload = JSON.parse(String(body || "").trim());
        if (
          payload &&
          (Array.isArray(payload.records) || Array.isArray(payload.errors))
        ) {
          cards.push(payload);
        }
      } catch (error) {
        console.warn("MAAT docs card konnte nicht gelesen werden", error);
      }
      return "\n\n";
    },
  );
  return { clean, cards };
}

function renderThinkingBox(thought, index, element) {
  const content = String(thought?.content || "").trim();
  const isOpen = element.dataset.thinkOpen === "true";
  const label = thought.complete ? "Denken anzeigen" : "Denken läuft...";
  const size = content.length ? ` · ${content.length.toLocaleString("de-DE")} Zeichen` : "";
  const live = thought.complete ? "" : " data-thinking-live=\"true\"";
  return (
    `<details class="think-box"${live} data-think-index="${index}"${isOpen ? " open" : ""}>` +
    `<summary><span>${escapeHtml(label)}</span><small>${escapeHtml(size || " · live")}</small></summary>` +
    `<div class="think-window"><pre class="think-raw">${escapeHtml(content || "...")}</pre></div>` +
    `</details>`
  );
}

function estimateProgressTokens(text) {
  const chars = String(text ?? "").length + 1200;
  return Math.max(1, Math.round(chars / 4));
}

function progressCardHtml({
  title = "MAAT verarbeitet den Kontext",
  tokens = 0,
  status = "Prompt wird vorbereitet",
  detail = "Die Antwort startet gleich. Diese Anzeige wird automatisch ersetzt.",
  kind = "prompt",
} = {}) {
  const tokenText = tokens ? `Prompt: ca. ${Number(tokens).toLocaleString("de-DE")} Tokens | ` : "";
  return (
    `<div class="maat-progress-card maat-progress-${escapeHtml(kind)}">` +
    `<div class="maat-progress-title"><span class="maat-progress-dot"></span>${escapeHtml(title)}</div>` +
    `<div class="maat-progress-meta">${escapeHtml(tokenText + status)}</div>` +
    `<div class="maat-progress-bar"><span></span></div>` +
    `<div class="maat-progress-detail">${escapeHtml(detail)}</div>` +
    `</div>`
  );
}

function setProgressCard(element, options = {}) {
  if (!element) return;
  element.dataset.progressActive = "true";
  element.dataset.rawContent = "";
  const content = element.querySelector(".message-content") || element;
  content.innerHTML = progressCardHtml(options);
  scrollMessagesToBottom();
}

function updateProgressCard(element, options = {}) {
  if (!element || element.dataset.progressActive !== "true") return;
  setProgressCard(element, options);
}

function clearProgressCard(element) {
  if (!element) return;
  delete element.dataset.progressActive;
}

function progressOptionsFromLog(payload = {}) {
  const source = String(payload.source || "");
  const title = String(payload.title || "");
  const lines = Array.isArray(payload.lines) ? payload.lines.map(String) : [];
  const joined = `${source}\n${title}\n${lines.join("\n")}`.toLowerCase();
  const modelLine = lines.find((line) => /^model=/i.test(line)) || "";
  const model = modelLine ? modelLine.replace(/^model=/i, "").trim() : "";

  if (joined.includes("cache=miss")) {
    return {
      title: "Erster Start Modell wird geladen.",
      status: model ? `Modell: ${model}` : "Modell wird in den RAM geladen",
      detail: "Beim ersten Start oder nach einem Modellwechsel lädt llama.cpp das GGUF-Modell. Danach ist es im Cache schneller.",
      kind: "model",
    };
  }
  if (joined.includes("modell bereit") || joined.includes("cache=hit")) {
    return {
      title: "Modell bereit",
      status: model ? `Modell: ${model}` : "Prompt wird verarbeitet",
      detail: "Das Modell ist geladen. Jetzt wird der Prompt ausgewertet, bis das erste Token erscheint.",
      kind: "ready",
    };
  }
  if (source === "progress" && joined.includes("prompt processing")) {
    return {
      title: "MAAT verarbeitet den Kontext",
      status: "Prompt Processing läuft",
      detail: "Das Backend evaluiert gerade Kontext, Memory und Prompt. Die Antwort startet nach dem ersten Token.",
      kind: "prompt",
    };
  }
  return null;
}

function maybeUpdateModelProgress(element, payload = {}) {
  if (!element || element.dataset.progressActive !== "true") return;
  const options = progressOptionsFromLog(payload);
  if (options) {
    updateProgressCard(element, options);
  }
}

function renderMessageContent(element, raw) {
  clearProgressCard(element);
  element.dataset.rawContent = raw ?? "";
  const content = element.querySelector(".message-content") || element;
  const role = element.dataset.role || "";
  if (role !== "assistant") {
    content.innerHTML = renderMessageWithAttachments(raw);
    attachCopyableBlockButtons(content);
    return;
  }

  const { answer, thoughts } = splitThinking(raw);
  const showThinking = thinkingEnabled();
  let html = "";

  if (showThinking && thoughts.length) {
    html += thoughts.map((thought, index) => renderThinkingBox(thought, index, element)).join("");
  }

  const memorySplit = splitMemorySaveBoxes(answer);
  const docsSplit = splitDocsCards(memorySplit.clean);
  const visibleAnswer = docsSplit.clean.trim();
  if (visibleAnswer) {
    html += `<div class="message-body">${renderMarkdown(visibleAnswer)}</div>`;
  } else if (!showThinking && thoughts.length) {
    html += '<div class="message-muted">Antwort wird vorbereitet...</div>';
  }
  for (const cardData of docsSplit.cards) {
    html += renderFileBuilderChatCard(cardData);
  }
  for (const box of memorySplit.boxes) {
    html += renderMemorySaveBox(box);
  }

  content.innerHTML = html || "";
  attachCopyableBlockButtons(content);
  attachFileBuilderCardHandlers(content);
  content.querySelectorAll(".think-box").forEach((box) => {
    const summary = box.querySelector("summary");
    summary?.addEventListener("pointerdown", () => {
      element.dataset.thinkOpen = box.open ? "false" : "true";
    });
    summary?.addEventListener("click", () => {
      element.dataset.thinkOpen = box.open ? "false" : "true";
      window.setTimeout(() => {
        element.dataset.thinkOpen = box.open ? "true" : "false";
      }, 0);
    });
    box.addEventListener("toggle", () => {
      element.dataset.thinkOpen = box.open ? "true" : "false";
      const pane = box.querySelector(".think-window");
      if (box.open && pane && box.dataset.thinkingLive === "true") {
        pane.scrollTop = pane.scrollHeight;
      }
    });
    const pane = box.querySelector(".think-window");
    if (box.open && pane && box.dataset.thinkingLive === "true") {
      pane.scrollTop = pane.scrollHeight;
    }
  });
}

function scrollMessagesToBottom() {
  requestAnimationFrame(() => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

function streamKey(chatId) {
  return chatId == null ? "__pending__" : String(chatId);
}

function sameChatId(a, b) {
  if (a == null || b == null) return a == null && b == null;
  return Number(a) === Number(b);
}

function streamForChat(chatId) {
  return activeStreams.get(streamKey(chatId)) || null;
}

function isViewingStream(stream) {
  return Boolean(stream) && sameChatId(currentChatId, stream.chatId);
}

function streamElementMounted(stream) {
  return Boolean(stream?.assistantElement && messagesEl.contains(stream.assistantElement));
}

function registerStream(stream) {
  activeStreams.set(streamKey(stream.chatId), stream);
}

function updateStreamChatId(stream, chatId) {
  if (!stream || chatId == null) return;
  const oldKey = streamKey(stream.chatId);
  const wasVisible = isViewingStream(stream);
  activeStreams.delete(oldKey);
  stream.chatId = chatId;
  activeStreams.set(streamKey(chatId), stream);
  if (wasVisible) {
    currentChatId = chatId;
    renderChatList();
  }
}

function ensureStreamAssistantElement(stream) {
  if (!isViewingStream(stream)) return null;
  if (!streamElementMounted(stream)) {
    stream.assistantElement = addMessage("assistant", stream.content || "");
  }
  return stream.assistantElement;
}

function renderStreamState(stream) {
  const element = ensureStreamAssistantElement(stream);
  if (!element) return;
  if (stream.content) {
    renderMessageContent(element, stream.content);
  } else if (stream.progressOptions) {
    setProgressCard(element, stream.progressOptions);
  } else {
    renderMessageContent(element, "");
  }
  for (const cardData of stream.fileBuilderCards || []) {
    appendFileBuilderChatCard(element, cardData);
  }
  scrollMessagesToBottom();
}

function updateStreamContent(stream, content) {
  if (!stream) return;
  stream.content = content || "";
  stream.progressOptions = null;
  const element = isViewingStream(stream) ? ensureStreamAssistantElement(stream) : null;
  if (element) {
    renderMessageContent(element, stream.content);
    for (const cardData of stream.fileBuilderCards || []) {
      appendFileBuilderChatCard(element, cardData);
    }
  }
}

function appendStreamToken(stream, token) {
  if (!stream || !token) return;
  updateStreamContent(stream, `${stream.content || ""}${token}`);
}

function updateStreamProgress(stream, options) {
  if (!stream || !options || stream.content) return;
  stream.progressOptions = options;
  const element = isViewingStream(stream) ? ensureStreamAssistantElement(stream) : null;
  if (element) setProgressCard(element, options);
}

function renderActiveStreamForChat(chatId) {
  const stream = streamForChat(chatId);
  if (!stream || (stream.done && !stream.stopped)) return;
  renderStreamState(stream);
}

function setSendButtonStreaming(streaming) {
  if (!sendButton) return;
  sendButton.disabled = false;
  sendButton.classList.toggle("stop-mode", Boolean(streaming));
  sendButton.textContent = streaming ? "Stop" : "Senden";
  sendButton.title = streaming ? "Antwort stoppen" : "Nachricht senden";
  sendButton.setAttribute("aria-label", streaming ? "Antwort stoppen" : "Nachricht senden");
}

const STREAM_LOCK_CONTROL_SELECTOR = [
  "#tab-model input",
  "#tab-model select",
  "#tab-model textarea",
  "#tab-model button",
  "#tab-settings input",
  "#tab-settings select",
  "#tab-settings textarea",
  "#tab-settings button",
  "#tab-maat input",
  "#tab-maat select",
  "#tab-maat textarea",
  "#tab-maat button",
  "#chatProjects input",
  "#chatProjects select",
  "#chatProjects textarea",
  "#chatProjects button",
  "#chatDocs input",
  "#chatDocs select",
  "#chatDocs textarea",
  "#chatDocs button",
].join(",");

function setConfigurationLocked(locked) {
  document.body.toggleAttribute("data-stream-config-locked", Boolean(locked));
  for (const control of document.querySelectorAll(STREAM_LOCK_CONTROL_SELECTOR)) {
    if (locked) {
      if (!control.dataset.streamLockActive) {
        control.dataset.streamLockActive = "1";
        control.dataset.streamLockWasDisabled = control.disabled ? "1" : "0";
      }
      control.disabled = true;
      continue;
    }
    if (control.dataset.streamLockActive) {
      control.disabled = control.dataset.streamLockWasDisabled === "1";
      delete control.dataset.streamLockActive;
      delete control.dataset.streamLockWasDisabled;
    }
  }
}

function stopCurrentStream() {
  if (!currentAbortController) return;
  currentAbortController.abort();
}

function activateTab(name) {
  for (const tab of document.querySelectorAll(".tab")) {
    tab.classList.toggle("active", tab.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.classList.toggle("active", panel.id === `tab-${name}`);
  }
  if (name === "chat") {
    scrollMessagesToBottom();
  } else if (name === "model") {
    loadGgufModels(false);
  } else if (name === "settings") {
    loadGgufModels(false);
  }
}

function addMessage(role, content = "") {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.dataset.role = role;

  const contentEl = document.createElement("div");
  contentEl.className = "message-content";
  el.appendChild(contentEl);

  if (role !== "system") {
    const actions = document.createElement("div");
    actions.className = "message-actions";

    const copyButton = document.createElement("button");
    copyButton.className = "message-action message-copy";
    copyButton.type = "button";
    copyButton.title = "Nachricht kopieren";
    copyButton.textContent = "Copy";
    copyButton.addEventListener("click", async () => {
      const ok = await copyText(visibleCopyText(el.dataset.rawContent || "", role));
      copyButton.textContent = ok ? "Kopiert" : "Fehler";
      setTimeout(() => {
        copyButton.textContent = "Copy";
      }, 1200);
    });

    const speakButton = document.createElement("button");
    speakButton.className = "message-action message-speak";
    speakButton.type = "button";
    speakButton.title = "Nachricht vorlesen";
    speakButton.textContent = "Vorlesen";
    speakButton.addEventListener("click", async () => {
      if (activeSpeakButton === speakButton) {
        await stopSpeaking();
        return;
      }
      if (activeSpeakButton) resetSpeakButton(activeSpeakButton);
      const text = visibleSpeakText(el.dataset.rawContent || "", role);
      const result = await speakText(text);
      speakButton.textContent = result?.ok ? "Stop" : "Fehler";
      if (!result?.ok) {
        statusLine.textContent = `Vorlesen fehlgeschlagen: ${result?.error || "unbekannter Fehler"}`;
      }
      if (result?.ok) {
        activeSpeakButton = speakButton;
        speakButton.classList.add("active");
        speakButton.title = "Vorlesen stoppen";
      } else {
        setTimeout(() => resetSpeakButton(speakButton), 1400);
      }
    });

    actions.append(copyButton, speakButton);
    el.appendChild(actions);
  }

  renderMessageContent(el, content);
  messagesEl.appendChild(el);
  scrollMessagesToBottom();
  return el;
}

function clearChatView(message = "Neuer Chat gestartet.") {
  currentChatId = null;
  messagesEl.innerHTML = "";
  clearChatLog();
  renderChatList();
  addMessage("system", message);
}

function renderStoredMessage(message) {
  if (!["user", "assistant", "system"].includes(message.role)) return;
  addMessage(message.role, message.content || "");
}

function renderChatList() {
  const query = (chatSearch.value || "").trim().toLowerCase();
  chatListEl.innerHTML = "";
  const chats = chatsCache.filter((chat) => {
    if (!query) return true;
    const haystack = `${chat.title || ""} ${chat.preview || ""}`.toLowerCase();
    return haystack.includes(query);
  });

  if (!chats.length) {
    const empty = document.createElement("div");
    empty.className = "chat-empty";
    empty.textContent = query ? "Keine passenden Chats." : "Noch keine Chats.";
    chatListEl.appendChild(empty);
    return;
  }

  for (const chat of chats) {
    const item = document.createElement("div");
    item.className = `chat-item${Number(chat.id) === Number(currentChatId) ? " active" : ""}`;
    item.dataset.chatId = chat.id;

    const button = document.createElement("button");
    button.className = "chat-item-main";
    button.type = "button";

    const title = document.createElement("div");
    title.className = "chat-item-title";
    title.textContent = chat.title || "Neuer Chat";

    const preview = document.createElement("div");
    preview.className = "chat-item-preview";
    preview.textContent = trimPreview(chat.preview || "Noch keine Antwort");

    const meta = document.createElement("div");
    meta.className = "chat-item-meta";
    const date = document.createElement("span");
    date.textContent = formatChatDate(chat.updated_at);
    const count = document.createElement("span");
    count.textContent = `${chat.message_count || 0} Msg`;
    meta.append(date, count);

    button.append(title, preview, meta);
    button.addEventListener("click", () => openChat(Number(chat.id)));

    const actions = document.createElement("div");
    actions.className = "chat-item-actions";

    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.title = "Chat umbenennen";
    renameButton.textContent = "✎";
    renameButton.addEventListener("click", (event) => {
      event.stopPropagation();
      renameChat(chat);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.title = "Chat löschen";
    deleteButton.textContent = "×";
    deleteButton.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteChat(chat);
    });

    actions.append(renameButton, deleteButton);
    item.append(button, actions);
    chatListEl.appendChild(item);
  }
}

async function loadChats() {
  const response = await fetch("/api/chats");
  const data = await response.json();
  chatsCache = data.chats || [];
  renderChatList();
}

async function openChat(chatId) {
  const response = await fetch(`/api/chat?chat_id=${encodeURIComponent(chatId)}`);
  const data = await response.json();
  if (!data.chat) {
    statusLine.textContent = "Chat nicht gefunden";
    return;
  }
  currentChatId = data.chat.id;
  messagesEl.innerHTML = "";
  for (const message of data.messages || []) {
    renderStoredMessage(message);
  }
  renderActiveStreamForChat(currentChatId);
  renderChatList();
  activateTab("chat");
  scrollMessagesToBottom();
  statusLine.textContent = `Chat geöffnet · ${data.chat.title || "Neuer Chat"}`;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function renameChat(chat) {
  const title = prompt("Neuer Chatname:", chat.title || "Neuer Chat");
  if (!title || !title.trim()) return;
  const data = await postJson("/api/chat/rename", { chat_id: chat.id, title: title.trim() });
  if (!data.ok) {
    statusLine.textContent = data.error || "Chat konnte nicht umbenannt werden";
    return;
  }
  statusLine.textContent = "Chat umbenannt";
  await loadChats();
}

async function deleteChat(chat) {
  const title = chat.title || "Neuer Chat";
  if (!confirm(`Chat wirklich löschen?\n\n${title}`)) return;
  const data = await postJson("/api/chat/delete", { chat_id: chat.id });
  if (!data.ok) {
    statusLine.textContent = data.error || "Chat konnte nicht gelöscht werden";
    return;
  }
  if (Number(currentChatId) === Number(chat.id)) {
    currentChatId = null;
    messagesEl.innerHTML = "";
    addMessage("system", "Chat gelöscht. Neuer Chat bereit.");
  }
  activeStreams.delete(streamKey(chat.id));
  statusLine.textContent = "Chat gelöscht";
  await loadChats();
}

function renderRuntime(state) {
  const runtime = document.querySelector("#runtime");
  runtime.innerHTML = "";
  const items = [
    ["Adapter", state.settings.model_adapter],
    ["Chats", state.database.chats],
    ["Messages", state.database.messages],
    ["Plugins", state.plugins.length],
  ];
  for (const [label, value] of items) {
    const row = document.createElement("div");
    row.className = "runtime-item";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    runtime.appendChild(row);
  }
}

function renderPlugins(plugins) {
  const list = document.querySelector("#plugins");
  list.innerHTML = "";
  for (const plugin of plugins) {
    const el = document.createElement("div");
    el.className = "plugin";
    const commands = plugin.commands.length ? plugin.commands.join(", ") : "keine Commands";
    el.innerHTML = `<strong>${plugin.id}</strong><span>${plugin.type} · ${commands}</span>`;
    list.appendChild(el);
  }
}

function favoritePaths() {
  const paths = stateCache?.settings?.favorite_model_paths;
  return Array.isArray(paths) ? paths : [];
}

function modelByPath(path) {
  return ggufModelsCache.find((model) => model.path === path);
}

function renderChatFavoriteModels() {
  chatFavoriteModel.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = favoritePaths().length ? "Favoritenmodell wählen..." : "Keine Modellfavoriten gesetzt";
  chatFavoriteModel.appendChild(placeholder);

  for (const path of favoritePaths()) {
    const model = modelByPath(path);
    const option = document.createElement("option");
    option.value = path;
    option.textContent = model?.name || shortPath(path);
    option.title = path;
    chatFavoriteModel.appendChild(option);
  }

  const current = stateCache?.settings?.llama_model_path || "";
  const hasCurrent = [...chatFavoriteModel.options].some((option) => option.value === current);
  chatFavoriteModel.value = hasCurrent ? current : "";
  chatModelMenuButton.classList.toggle("active", Boolean(hasCurrent));
}

function renderFavoriteModels() {
  const containers = [...document.querySelectorAll("#favoriteModels, #modelFavoriteModels")];
  if (!containers.length) return;
  for (const container of containers) renderFavoriteModelsInto(container);
}

function syncFavoriteCheckboxes(path, checked) {
  for (const box of document.querySelectorAll("#favoriteModels input, #modelFavoriteModels input")) {
    if (box.value === path) box.checked = checked;
  }
}

function renderFavoriteModelsInto(container) {
  container.innerHTML = "";

  const selected = new Set(favoritePaths());
  const visiblePaths = new Set(ggufModelsCache.map((model) => model.path));
  const missingFavorites = favoritePaths().filter((path) => !visiblePaths.has(path));

  if (!ggufModelsCache.length) {
    if (!missingFavorites.length) {
      const empty = document.createElement("div");
      empty.className = "chat-empty";
      empty.textContent = "Noch keine GGUF-Liste geladen.";
      container.appendChild(empty);
      return;
    }
  }

  for (const path of missingFavorites) {
    const label = document.createElement("label");
    label.className = "favorite-model";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = path;
    checkbox.checked = true;
    checkbox.dataset.missingFavorite = "true";
    checkbox.addEventListener("change", () => {
      syncFavoriteCheckboxes(checkbox.value, checkbox.checked);
      stateCache.settings.favorite_model_paths = favoritePayload();
      renderChatFavoriteModels();
      renderFavoriteModels();
    });

    const text = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = `${shortPath(path)} · gespeicherter Favorit`;
    const smallPath = document.createElement("small");
    smallPath.textContent = path;
    text.append(name, smallPath);
    label.append(checkbox, text);
    container.appendChild(label);
  }

  for (const model of ggufModelsCache) {
    const label = document.createElement("label");
    label.className = "favorite-model";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = model.path;
    checkbox.checked = selected.has(model.path);
    checkbox.addEventListener("change", () => {
      syncFavoriteCheckboxes(checkbox.value, checkbox.checked);
      stateCache.settings.favorite_model_paths = favoritePayload();
      renderChatFavoriteModels();
      renderFavoriteModels();
    });

    const text = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = model.name;
    const path = document.createElement("small");
    path.textContent = model.path;
    text.append(name, path);
    label.append(checkbox, text);
    container.appendChild(label);
  }
}

function updateThinkingControls() {
  const enabled = Boolean(stateCache?.settings?.enable_thinking);
  const enableThinking = document.querySelector("#enableThinking");
  if (enableThinking) enableThinking.checked = enabled;
  if (chatThinkingToggle) {
    chatThinkingToggle.classList.toggle("active", enabled);
    chatThinkingToggle.textContent = enabled ? "Think an" : "Think aus";
    chatThinkingToggle.title = enabled
      ? "Thinking ist aktiv. Klicken zum Ausschalten."
      : "Thinking ist aus. Klicken zum Einschalten.";
  }
}

async function saveThinkingSetting(enabled) {
  if (!stateCache?.settings) return false;
  if (isSending) {
    statusLine.textContent = "Thinking kann während des Streamings nicht umgeschaltet werden.";
    updateThinkingControls();
    return false;
  }
  const previous = Boolean(stateCache.settings.enable_thinking);
  stateCache.settings.enable_thinking = Boolean(enabled);
  updateThinkingControls();
  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enable_thinking: Boolean(enabled) }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (data.settings) {
      stateCache.settings = data.settings;
    }
    updateThinkingControls();
    statusLine.textContent = stateCache.settings.enable_thinking ? "Thinking aktiviert" : "Thinking deaktiviert";
    return true;
  } catch (error) {
    stateCache.settings.enable_thinking = previous;
    updateThinkingControls();
    statusLine.textContent = `Thinking konnte nicht gespeichert werden: ${error.message}`;
    return false;
  }
}

function maatThinkingInfo(levelValue) {
  const raw = Number(levelValue || 0);
  const level = Math.max(0, Math.min(100, Number.isFinite(raw) ? Math.round(raw) : 0));
  if (level <= 0) return {
    label: "MAAT0",
    text: "MAAT Thinking aus · keine zusätzliche MAAT-Qualitätsprüfung im Prompt",
  };
  const depth = level < 35 ? "light" : level < 75 ? "balanced" : "deep";
  const repairs = level < 40 ? 1 : level < 80 ? 2 : 3;
  const target = (6.8 + (2.7 * (level / 100))).toFixed(1);
  return {
    label: `MAAT${level}`,
    text: `MAAT${level} aktiv · ${depth} · Zielwert ${target} · ${repairs} Repair-Runde${repairs === 1 ? "" : "n"}`,
  };
}

function updateMaatThinkingControls() {
  const raw = Number(stateCache?.settings?.maat_thinking_level || 0);
  const level = Math.max(0, Math.min(100, Number.isFinite(raw) ? Math.round(raw) : 0));
  if (maatThinkingLevel) maatThinkingLevel.value = String(level);
  if (maatThinkingLevelValue) maatThinkingLevelValue.textContent = `${level}%`;
  if (maatThinkSlider) maatThinkSlider.value = String(level);
  if (maatThinkSliderValue) maatThinkSliderValue.textContent = `${level}%`;
  maatThinkOff?.classList.toggle("active", level === 0);
  maatThinkingOff?.classList.toggle("active", level === 0);
  const info = maatThinkingInfo(level);
  if (maatThinkingStatus) maatThinkingStatus.textContent = info.text;
}

function updateContextOptimizerControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.context_optimizer_enabled !== false;
  if (contextOptimizerEnabled) contextOptimizerEnabled.checked = enabled;
  if (contextOptimizerDebug) contextOptimizerDebug.checked = Boolean(settings.context_optimizer_debug);
  if (contextOptimizerUserBlock) contextOptimizerUserBlock.checked = settings.context_optimizer_current_user_block !== false;
  if (contextOptimizerMaxMemoryItems) contextOptimizerMaxMemoryItems.value = settings.context_optimizer_max_memory_items ?? 6;
  if (contextOptimizerMaxMemoryChars) contextOptimizerMaxMemoryChars.value = settings.context_optimizer_max_memory_chars ?? 2600;
  if (contextOptimizerStatus) {
    contextOptimizerStatus.textContent = state.maat_context_optimizer?.status || (
      enabled
        ? `Context Optimizer aktiv · Memory ${settings.context_optimizer_max_memory_items ?? 6} Items/${settings.context_optimizer_max_memory_chars ?? 2600} Zeichen`
        : "Context Optimizer aus"
    );
  }
}

function updateSpiritControls(settings = stateCache?.settings || {}) {
  const enabled = Boolean(settings.spirit_enabled);
  if (spiritEnabled) spiritEnabled.checked = enabled;
  if (spiritMode) spiritMode.value = settings.spirit_mode || "standard";
  if (spiritLanguage) spiritLanguage.value = settings.spirit_language || "auto";
  if (spiritOnce) spiritOnce.checked = settings.spirit_once !== false;
  if (spiritUseEmojis) spiritUseEmojis.checked = settings.spirit_use_emojis !== false;
  if (spiritStatus) {
    const mode = settings.spirit_mode || "standard";
    const lang = settings.spirit_language || "auto";
    const once = settings.spirit_once !== false ? "einmalig voll" : "immer voll";
    spiritStatus.textContent = enabled
      ? `MAAT Spirit aktiv · ${mode} · Sprache ${lang} · ${once}`
      : "MAAT Spirit aus · kein zusätzlicher Spirit-Kontext";
  }
}

function updateSuperMemoryControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.supermem_enabled !== false;
  const currentUser = normalizeUserName(settings.supermem_current_user || "User");
  const users = knownUsersFromSettings({ ...settings, supermem_current_user: currentUser });
  if (supermemEnabled) supermemEnabled.checked = enabled;
  if (supermemAutostore) supermemAutostore.checked = settings.supermem_autostore !== false;
  if (supermemAutorecall) supermemAutorecall.checked = settings.supermem_autorecall !== false;
  if (supermemDebug) supermemDebug.checked = Boolean(settings.supermem_debug);
  if (supermemModelSaves) supermemModelSaves.checked = settings.supermem_allow_model_saves !== false;
  if (supermemSaveBox) supermemSaveBox.checked = settings.supermem_show_save_box !== false;
  if (supermemDreaming) supermemDreaming.checked = settings.supermem_dreaming_enabled !== false;
  if (supermemDreamOnLoad) supermemDreamOnLoad.checked = Boolean(settings.supermem_dream_on_load);
  if (supermemArchive) supermemArchive.checked = settings.supermem_archive_enabled !== false;
  if (supermemPersonRecall) supermemPersonRecall.checked = settings.supermem_person_recall !== false;
  if (supermemPersonGraph) supermemPersonGraph.checked = settings.supermem_person_graph !== false;
  renderUserSelect(supermemCurrentUser, users, currentUser);
  renderUserSelect(chatCurrentUser, users, currentUser);
  renderUserSelect(personGraphSourceUser, users, personGraphSelectedUser() || currentUser);
  if (supermemTopK) supermemTopK.value = settings.supermem_top_k ?? 5;
  if (supermemMinScore) supermemMinScore.value = settings.supermem_min_score ?? 0.15;
  if (supermemGraphTopK) supermemGraphTopK.value = settings.supermem_person_graph_top_k ?? 2;
  if (supermemPersonTopK) supermemPersonTopK.value = settings.supermem_person_top_k ?? 4;
  if (supermemUserBonus) supermemUserBonus.value = settings.supermem_user_memory_bonus ?? 0.12;
  if (supermemMaxMemories) supermemMaxMemories.value = settings.supermem_max_memories ?? 1000;
  if (supermemDreamHours) supermemDreamHours.value = settings.supermem_dream_hours ?? 24;
  if (supermemArchiveDays) supermemArchiveDays.value = settings.supermem_archive_after_days ?? 30;
  syncKnownUsersField({ ...settings, supermem_known_users: users.join(", "), supermem_current_user: currentUser });
  if (supermemPersonNames) supermemPersonNames.value = splitLooseList(settings.supermem_person_names || "").join(", ");
  if (supermemAmbiguousNames) supermemAmbiguousNames.value = splitLooseList(settings.supermem_person_ambiguous_names || "").join(", ");
  if (supermemStatus) {
    const memory = state.super_memory || {};
    const layers = memory.layers || {};
    const total = Object.values(layers).reduce((sum, value) => sum + Number(value || 0), 0);
    supermemStatus.textContent = enabled
      ? `Super Memory aktiv · User ${currentUser} · ${total} Saves · Working ${memory.working || 0} · Graph ${memory.person_graph || 0} · Archiv ${memory.monthly_archive || 0}`
      : "Super Memory aus · kein Memory-Kontext";
  }
  if (supermemDreamStatus && !supermemDreamStatus.dataset.busy) {
    supermemDreamStatus.textContent = settings.supermem_dreaming_enabled !== false
      ? `Dreaming bereit · Archiv ${state.super_memory?.monthly_archive || 0}/${state.super_memory?.archived_sources || 0}`
      : "Dreaming aus.";
  }
}

function updateStyleControls(settings = stateCache?.settings || {}) {
  const enabled = settings.style_enabled !== false;
  if (styleEnabled) styleEnabled.checked = enabled;
  if (styleDebug) styleDebug.checked = Boolean(settings.style_debug);
  if (styleGreetingOverride) styleGreetingOverride.checked = settings.style_greeting_override !== false;
  if (styleToneAuto) styleToneAuto.checked = settings.style_tone_auto !== false;
  if (styleToneMode) styleToneMode.value = settings.style_tone_mode || "friendly";
  if (styleOpeningMode) styleOpeningMode.value = settings.style_opening_mode || "varied";
  if (styleDensityMode) styleDensityMode.value = settings.style_density_mode || "normal";
  if (styleHeadingMode) styleHeadingMode.value = settings.style_heading_mode || "simple";
  if (styleListMode) styleListMode.value = settings.style_list_mode || "auto";
  if (styleEmojiMode) styleEmojiMode.value = settings.style_emoji_mode || "few";
  if (styleOldSmileyMode) styleOldSmileyMode.value = settings.style_old_smiley_mode || "none";
  if (styleStatus) {
    styleStatus.textContent = enabled
      ? `MAAT Style aktiv · Ton ${settings.style_tone_mode || "friendly"} · Anrede ${settings.style_opening_mode || "varied"} · Emojis ${settings.style_emoji_mode || "few"} · Smileys ${settings.style_old_smiley_mode || "none"}`
      : "MAAT Style aus · keine Intent-/Formatsteuerung";
  }
}

function updateRewriteControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.rewrite_enabled !== false;
  if (rewriteEnabled) rewriteEnabled.checked = enabled;
  if (rewriteTrimOutputs) rewriteTrimOutputs.checked = Boolean(settings.rewrite_trim_outputs);
  if (rewriteShowBanner) rewriteShowBanner.checked = Boolean(settings.rewrite_show_banner);
  if (rewriteMode) rewriteMode.value = settings.rewrite_mode || "light";
  if (rewriteFieldWeak) rewriteFieldWeak.value = settings.rewrite_field_weak ?? 6.2;
  if (rewriteFieldStrong) rewriteFieldStrong.value = settings.rewrite_field_strong ?? 5.0;
  if (rewriteRMin) rewriteRMin.value = settings.rewrite_r_min ?? 7.0;
  if (rewriteStatus) {
    const last = state.maat_rewrite?.last_eval;
    const tail = last ? ` · last ${last.action || "pass"}${last.changed ? " · geändert" : ""}` : "";
    rewriteStatus.textContent = state.maat_rewrite?.status || (
      enabled
        ? `MAAT Rewrite aktiv · ${settings.rewrite_mode || "light"} · Kürzen ${settings.rewrite_trim_outputs ? "an" : "aus"}${tail}`
        : "MAAT Rewrite aus"
    );
  }
}

function updateCoreControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.maat_core_enabled !== false;
  if (coreEnabled) coreEnabled.checked = enabled;
  if (coreMode) coreMode.value = settings.maat_core_mode || "standard";
  if (coreStatus) {
    coreStatus.textContent = state.maat_core?.status || (
      enabled
        ? `MAAT Value Core aktiv · ${settings.maat_core_mode || "standard"}`
        : "MAAT Value Core aus"
    );
  }
}

function updateRealityControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.reality_enabled !== false;
  if (realityEnabled) realityEnabled.checked = enabled;
  if (realityInjectTime) realityInjectTime.checked = settings.reality_inject_time !== false;
  if (realityShowBanner) realityShowBanner.checked = Boolean(settings.reality_show_banner);
  if (realityStatus) {
    const reality = state.maat_reality || {};
    realityStatus.textContent = reality.status || (
      enabled
        ? `MAAT Reality aktiv · ${reality.weekday || ""} ${reality.date || ""} ${reality.time || ""}`.trim()
        : "MAAT Reality aus"
    );
  }
}

function updateBalanceControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.balance_enabled !== false;
  if (balanceEnabled) balanceEnabled.checked = enabled;
  if (balanceDebug) balanceDebug.checked = Boolean(settings.balance_debug);
  if (balanceOnce) balanceOnce.checked = Boolean(settings.balance_once);
  if (balanceSelfReflect) balanceSelfReflect.checked = settings.balance_self_reflect !== false;
  if (balanceDynamic) balanceDynamic.checked = settings.balance_dynamic !== false;
  if (balanceContextWeights) balanceContextWeights.checked = settings.balance_context_weights !== false;
  if (balanceCounterpartMode) balanceCounterpartMode.checked = settings.balance_counterpart_mode !== false;
  if (balanceLevel) balanceLevel.value = settings.balance_level || "standard";
  if (balanceStatus) {
    balanceStatus.textContent = state.maat_balance?.status || (
      enabled
        ? `MAAT Balance aktiv · ${settings.balance_level || "standard"} · B_dynamic ${settings.balance_dynamic !== false ? "an" : "aus"}`
        : "MAAT Balance aus"
    );
  }
}

function updateClaimGuardControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.claim_guard_enabled !== false;
  if (claimGuardEnabled) claimGuardEnabled.checked = enabled;
  if (claimGuardAfterOutput) claimGuardAfterOutput.checked = settings.claim_guard_after_output !== false;
  if (claimGuardBanner) claimGuardBanner.checked = Boolean(settings.claim_guard_show_banner);
  if (claimGuardMode) claimGuardMode.value = settings.claim_guard_mode || "balanced";
  if (claimGuardStatus) {
    const last = state.maat_claim_guard?.last_eval;
    const tail = last
      ? ` · last ${last.stance || "normal"} · risk ${last.risk_level || "-"}${last.changed ? " · repariert" : ""}`
      : "";
    claimGuardStatus.textContent = state.maat_claim_guard?.status || (
      enabled
        ? `Claim Guard aktiv · ${settings.claim_guard_mode || "balanced"} · Output ${settings.claim_guard_after_output !== false ? "an" : "aus"}${tail}`
        : "Claim Guard aus"
    );
  }
}

function updateAdaptiveLearningControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.adaptive_learning_enabled !== false;
  const learning = state.maat_adaptive_learning || {};
  if (adaptiveLearningEnabled) adaptiveLearningEnabled.checked = enabled;
  if (adaptiveLearningInject) adaptiveLearningInject.checked = settings.adaptive_learning_inject !== false;
  if (adaptiveLearningDebug) adaptiveLearningDebug.checked = Boolean(settings.adaptive_learning_debug);
  if (adaptiveLearningPerTurn) adaptiveLearningPerTurn.value = settings.adaptive_learning_per_turn ?? 2;
  if (adaptiveLearningExplore) adaptiveLearningExplore.value = settings.adaptive_learning_exploration_rate ?? 0.25;
  if (adaptiveLearningUserBonus) adaptiveLearningUserBonus.value = settings.adaptive_learning_user_bonus ?? 0.2;
  if (adaptiveLearningStatus) {
    const last = learning.last_why || {};
    const lessonCount = Array.isArray(last.lessons) ? last.lessons.length : 0;
    const hintCount = Array.isArray(last.hints) ? last.hints.length : 0;
    adaptiveLearningStatus.textContent = enabled
      ? `Adaptive Learning aktiv · ${learning.active ?? 0} Lessons · ${settings.adaptive_learning_per_turn ?? 2}/Antwort · last ${lessonCount} Lessons/${hintCount} Hints`
      : "Adaptive Learning aus";
  }
}

function updateFeedbackControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.feedback_enabled !== false;
  const feedback = state.maat_feedback_tool || {};
  if (feedbackEnabled) feedbackEnabled.checked = enabled;
  if (feedbackDebug) feedbackDebug.checked = Boolean(settings.feedback_debug);
  if (feedbackSelfLearning) feedbackSelfLearning.checked = settings.feedback_self_learning_enabled !== false;
  if (feedbackHistoryLimit) feedbackHistoryLimit.value = settings.feedback_history_limit ?? 25;
  if (feedbackWarnB) feedbackWarnB.value = settings.feedback_warn_below_b ?? 0.6;
  if (feedbackWarnR) feedbackWarnR.value = settings.feedback_warn_below_r ?? 0.75;
  if (feedbackWarnH) feedbackWarnH.value = settings.feedback_warn_below_h ?? 0.65;
  if (feedbackSelfPerReport) feedbackSelfPerReport.value = settings.feedback_self_learning_per_report ?? 2;
  if (feedbackStatus) {
    const last = feedback.last || feedback.last_report || {};
    const lastTail = last?.scores
      ? ` · last H${Number(last.scores.H || 0).toFixed(2)} B${Number(last.scores.B || 0).toFixed(2)} R${Number(last.scores.R || 0).toFixed(2)}${last.critical ? " · kritisch" : ""}`
      : "";
    feedbackStatus.textContent = enabled
      ? `MAAT Feedback aktiv · Reports ${feedback.history ?? 0} · Self-Lessons ${settings.feedback_self_learning_enabled !== false ? "an" : "aus"}${lastTail}`
      : "MAAT Feedback aus";
  }
}

function updateProjectMemoryControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  if (projectMemoryEnabled) projectMemoryEnabled.checked = settings.project_memory_enabled !== false;
  if (projectMemoryDebug) projectMemoryDebug.checked = Boolean(settings.project_memory_debug);
  if (projectMemoryTopK) projectMemoryTopK.value = settings.project_memory_top_k ?? 2;
  if (projectMemoryMaxChars) projectMemoryMaxChars.value = settings.project_memory_max_chars ?? 2600;
  if (state.maat_project_memory && chatProjectsEl && !chatProjectsEl.hidden) {
    renderProjectsPanel(state.maat_project_memory);
  }
}

function updateFileBuilderControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  if (fileBuilderEnabled) fileBuilderEnabled.checked = settings.file_builder_enabled !== false;
  if (fileBuilderInject) fileBuilderInject.checked = settings.file_builder_inject_instructions !== false;
  if (fileBuilderReplace) fileBuilderReplace.checked = settings.file_builder_replace_blocks !== false;
  if (fileBuilderSource) fileBuilderSource.checked = settings.file_builder_show_source_code !== false;
  if (fileBuilderFences) fileBuilderFences.checked = settings.file_builder_auto_capture_fences !== false;
  if (fileBuilderCompileTex) fileBuilderCompileTex.checked = settings.file_builder_compile_tex_pdf !== false;
  if (fileBuilderPythonCheck) fileBuilderPythonCheck.checked = settings.file_builder_python_syntax_check !== false;
  if (fileBuilderPythonRun) fileBuilderPythonRun.checked = settings.file_builder_python_run_enabled !== false;
  if (fileBuilderTerminal) fileBuilderTerminal.checked = settings.file_builder_python_run_in_terminal !== false;
  if (fileBuilderFeedback) fileBuilderFeedback.checked = settings.file_builder_inject_feedback !== false;
  if (fileBuilderDebug) fileBuilderDebug.checked = Boolean(settings.file_builder_debug);
  if (fileBuilderPreviewChars) fileBuilderPreviewChars.value = settings.file_builder_preview_chars ?? 5000;
  if (state.maat_file_builder && chatDocsEl && !chatDocsEl.hidden) {
    renderDocsPanel(state.maat_file_builder);
  }
}

function updateEmotionControls(settings = stateCache?.settings || {}) {
  const enabled = settings.emotion_enabled !== false;
  if (emotionEnabled) emotionEnabled.checked = enabled;
  if (emotionDebug) emotionDebug.checked = Boolean(settings.emotion_debug);
  if (emotionMode) emotionMode.value = settings.emotion_mode || "full";
  if (emotionLanguage) emotionLanguage.value = settings.emotion_language || "auto";
  if (emotionStatus) {
    emotionStatus.textContent = enabled
      ? `MAAT Emotion aktiv · ${settings.emotion_mode || "full"} · Sprache ${settings.emotion_language || "auto"} · R=10`
      : "MAAT Emotion aus · keine Emotionssteuerung";
  }
}

function updateOfflineWikiControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = Boolean(settings.offline_wiki_enabled);
  if (offlineWikiEnabled) offlineWikiEnabled.checked = enabled;
  if (offlineWikiAuto) offlineWikiAuto.checked = settings.offline_wiki_auto !== false;
  if (offlineWikiDebug) offlineWikiDebug.checked = Boolean(settings.offline_wiki_debug);
  if (offlineWikiLog) offlineWikiLog.checked = settings.offline_wiki_log !== false;
  if (offlineWikiPath) offlineWikiPath.value = settings.offline_wiki_zim_path || "";
  if (offlineWikiMaxChars) offlineWikiMaxChars.value = settings.offline_wiki_max_chars ?? 1400;
  if (offlineWikiMultiMaxChars) offlineWikiMultiMaxChars.value = settings.offline_wiki_multi_max_chars ?? 700;
  if (offlineWikiMaxTerms) offlineWikiMaxTerms.value = settings.offline_wiki_max_terms ?? 2;
  if (offlineWikiStatus) {
    offlineWikiStatus.textContent = state.offline_wiki?.status || (enabled ? "Offline Wiki aktiv." : "Offline Wiki aus.");
  }
}

function updateIdentityControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.identity_enabled !== false;
  if (identityEnabled) identityEnabled.checked = enabled;
  if (identityOnce) identityOnce.checked = settings.identity_once !== false;
  if (identityName) identityName.value = settings.identity_name || "MAAT-KI";
  if (identityMode) identityMode.value = settings.identity_mode || "balanced";
  if (identityStatus) {
    identityStatus.textContent = state.maat_identity?.status || (
      enabled
        ? `MAAT Identity aktiv · ${settings.identity_name || "MAAT-KI"} · ${settings.identity_mode || "balanced"}`
        : "MAAT Identity aus"
    );
  }
}

function formatEngineReport(result) {
  if (!result) return "Noch keine Antwort analysiert.";
  const settings = stateCache?.settings || {};
  const lines = [
    result.text || "",
    `Maat Value=${Number(result.maat_value ?? 0).toFixed(2)}`,
    result.diagnosis || "",
  ];
  if (settings.engine_show_cci_debug) {
    lines.push(`CCI_runtime=${Number(result.cci_runtime ?? 0).toFixed(3)} state=${result.cci_state || "n/a"} hint=${result.cci_hint || "ok"}`);
  }
  const advanced = stateCache?.maat_cci?.last_eval;
  if (settings.advanced_cci_enabled && settings.advanced_cci_show_debug && advanced) {
    const components = advanced.components || {};
    lines.push(advanced.text || `Advanced CCI=${Number(advanced.cci ?? 0).toFixed(4)} → ${advanced.regime || "n/a"}`);
    lines.push(
      `components: inst=${Number(components.inst ?? 0).toFixed(2)} prod=${Number(components.prod ?? 0).toFixed(2)} coh=${Number(components.coh ?? 0).toFixed(2)} cons=${Number(components.cons ?? 0).toFixed(2)} corr=${Number(components.corr ?? 0).toFixed(2)} int=${Number(components.int ?? 0).toFixed(2)} U_struct=${Number(components.U_struct ?? 0).toFixed(3)}`,
    );
  }
  return lines
    .filter(Boolean)
    .join("\n");
}

function updateEngineControls(state = stateCache || {}) {
  const settings = state.settings || {};
  const engine = state.maat_engine || {};
  if (engineEnabled) engineEnabled.checked = Boolean(settings.engine_enabled);
  if (engineShowInChat) engineShowInChat.checked = Boolean(settings.engine_show_in_chat);
  if (engineShowCciDebug) engineShowCciDebug.checked = Boolean(settings.engine_show_cci_debug);
  if (advancedCciEnabled) advancedCciEnabled.checked = settings.advanced_cci_enabled !== false;
  if (advancedCciShowDebug) advancedCciShowDebug.checked = Boolean(settings.advanced_cci_show_debug);
  if (advancedCciKappa) advancedCciKappa.value = settings.advanced_cci_kappa ?? 0.5;
  if (engineLastReport) engineLastReport.textContent = formatEngineReport(engine.last_eval);
}

function updateReflectionControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  if (reflectionEnabled) reflectionEnabled.checked = settings.reflection_enabled !== false;
  if (reflectionBanner) reflectionBanner.checked = Boolean(settings.reflection_banner);
  if (reflectionPromptRule) reflectionPromptRule.checked = settings.reflection_prompt_rule !== false;
  if (reflectionMode) reflectionMode.value = settings.reflection_mode || "auto";
  if (reflectionStatus) {
    const last = state.maat_reflection?.last_eval?.text || "noch keine Scores";
    reflectionStatus.textContent = state.maat_reflection?.status || `MAAT Reflection · ${last}`;
  }
}

function updateAntiHalluControls(settings = stateCache?.settings || {}, state = stateCache || {}) {
  const enabled = settings.antihallu_enabled !== false;
  if (antihalluEnabled) antihalluEnabled.checked = enabled;
  if (antihalluBanner) antihalluBanner.checked = Boolean(settings.antihallu_show_banner);
  if (antihalluGaps) antihalluGaps.checked = settings.antihallu_gap_questions !== false;
  if (antihalluSymbolic) antihalluSymbolic.checked = settings.antihallu_symbolic_lenient !== false;
  if (antihalluMode) antihalluMode.value = settings.antihallu_mode || "soften";
  if (antihalluSoftenThreshold) antihalluSoftenThreshold.value = settings.antihallu_soften_threshold ?? 0.55;
  if (antihalluStrictThreshold) antihalluStrictThreshold.value = settings.antihallu_strict_threshold ?? 0.85;
  if (antihalluStatus) {
    const last = state.maat_antihallu?.last_eval?.text || "noch keine Antwort geprüft";
    antihalluStatus.textContent = state.maat_antihallu?.status || (
      enabled
        ? `PLP Anti-Hallu aktiv · ${settings.antihallu_mode || "soften"} · ${last}`
        : "PLP Anti-Hallu aus"
    );
  }
}

async function setMaatThinkingLevel(level) {
  if (!stateCache?.settings) return;
  const raw = Number(level || 0);
  const normalized = Math.max(0, Math.min(100, Number.isFinite(raw) ? Math.round(raw) : 0));
  stateCache.settings.maat_thinking_level = normalized;
  updateMaatThinkingControls();
  await saveSettings();
  statusLine.textContent = `${maatThinkingInfo(normalized).label} gespeichert`;
}

function previewMaatThinkingLevel(level) {
  if (!stateCache?.settings) return;
  const raw = Number(level || 0);
  stateCache.settings.maat_thinking_level = Math.max(0, Math.min(100, Number.isFinite(raw) ? Math.round(raw) : 0));
  updateMaatThinkingControls();
}

function updateMaxTokenControls() {
  const auto = Boolean(document.querySelector("#maxTokensFromCtx")?.checked);
  const maxTokens = document.querySelector("#maxTokens");
  if (!maxTokens) return;
  maxTokens.disabled = auto;
  maxTokens.title = auto ? "Wird automatisch aus CTX minus Promptreserve berechnet" : "";
}

function scanSummaryText(scan = {}) {
  const recommended = scan.recommended || {};
  const current = scan.current || {};
  const gpu = scan.gpu || {};
  const parts = [
    scan.profile ? `Profil ${scan.profile}` : "",
    scan.distro ? scan.distro : "",
    scan.memory ? `RAM ${scan.memory}` : "",
    scan.cpu_count ? `CPU ${scan.cpu_count}` : "",
    gpu.kind && gpu.kind !== "none" ? `GPU ${gpu.kind}` : "",
    `Threads ${recommended.llama_n_threads ?? current.llama_n_threads ?? "-"}`,
    `GPU-Layers ${recommended.llama_n_gpu_layers ?? current.llama_n_gpu_layers ?? "-"}`,
    recommended.model_quant ? `Modell ${recommended.model_quant}` : "",
    `CTX-Empfehlung ${recommended.ctx_recommendation ?? recommended.model_ctx ?? "-"}`,
  ].filter(Boolean);
  return parts.join(" · ");
}

function updateLoaderTuningControls(settings = stateCache?.settings || {}, scan = stateCache?.system_scan || {}) {
  const mode = settings.loader_tuning_mode === "auto" ? "auto" : "manual";
  loaderAutoMode?.classList.toggle("active", mode === "auto");
  loaderManualMode?.classList.toggle("active", mode !== "auto");
  const threads = document.querySelector("#llamaNThreads");
  const gpuLayers = document.querySelector("#llamaNGpuLayers");
  if (threads) {
    threads.disabled = mode === "auto";
    threads.title = mode === "auto" ? "Wird im Auto-Modus vom Systemscan gesetzt" : "";
  }
  if (gpuLayers) {
    gpuLayers.disabled = mode === "auto";
    gpuLayers.title = mode === "auto" ? "Wird im Auto-Modus vom Systemscan gesetzt" : "";
  }
  if (systemScanSummary) {
    const summary = scanSummaryText(scan);
    const note = Array.isArray(scan.notes) && scan.notes.length ? ` · ${scan.notes[0]}` : "";
    systemScanSummary.textContent = summary
      ? `${mode === "auto" ? "Auto aktiv" : "Manuell"} · ${summary}${note}`
      : "Auto setzt Threads/GPU-Layers passend zum System. CTX bleibt separat.";
  }
}

async function setLoaderTuningMode(mode) {
  if (!stateCache?.settings) return;
  stateCache.settings.loader_tuning_mode = mode === "auto" ? "auto" : "manual";
  updateLoaderTuningControls(stateCache.settings, stateCache.system_scan || {});
  await saveSettings(saveSettingsStatus);
}

async function applySystemScan() {
  if (!runSystemScan) return;
  runSystemScan.disabled = true;
  if (systemScanStatus) systemScanStatus.textContent = "scannt...";
  try {
    const data = await fetchJson("/api/system-scan/apply", { method: "POST" });
    if (data.settings) stateCache.settings = data.settings;
    if (data.system_scan) stateCache.system_scan = data.system_scan;
    fillSettings(stateCache.settings);
    if (systemScanStatus) systemScanStatus.textContent = "Auto übernommen";
    statusLine.textContent = "Systemscan übernommen. CTX bleibt manuell gesetzt.";
  } catch (error) {
    if (systemScanStatus) systemScanStatus.textContent = error.message || String(error);
  } finally {
    runSystemScan.disabled = false;
  }
}

async function restartMaatWebCore() {
  if (!restartWebCore) return;
  const ok = window.confirm("MAAT Web Core jetzt komplett neu starten?");
  if (!ok) return;
  restartWebCore.disabled = true;
  if (saveSettingsStatus) saveSettingsStatus.textContent = "Restart wird angefordert...";
  statusLine.textContent = "MAAT Web Core startet neu...";
  try {
    await fetchJson("/api/restart", { method: "POST" });
    if (saveSettingsStatus) saveSettingsStatus.textContent = "Restart läuft...";
  } catch (error) {
    if (saveSettingsStatus) saveSettingsStatus.textContent = error.message || String(error);
    restartWebCore.disabled = false;
    return;
  }

  const started = Date.now();
  const poll = async () => {
    try {
      const response = await fetch(`/api/state?restart=${Date.now()}`, { cache: "no-store" });
      if (response.ok && Date.now() - started > 1400) {
        statusLine.textContent = "MAAT Web Core ist wieder da. Lade Oberfläche neu...";
        window.location.reload();
        return;
      }
    } catch (_) {
      // Expected while the process is being replaced.
    }
    if (Date.now() - started > 30000) {
      if (saveSettingsStatus) saveSettingsStatus.textContent = "Restart dauert länger. Bitte Seite manuell neu laden.";
      statusLine.textContent = "Restart dauert länger. Browserseite kann gleich neu geladen werden.";
      restartWebCore.disabled = false;
      return;
    }
    setTimeout(poll, 900);
  };
  setTimeout(poll, 1200);
}

function syncCtxInputs(source) {
  const modelCtx = document.querySelector("#llamaNCtx");
  const settingsCtx = document.querySelector("#settingsNCtx");
  if (!modelCtx || !settingsCtx) return;
  if (source === "settings") {
    modelCtx.value = settingsCtx.value;
  } else {
    settingsCtx.value = modelCtx.value;
  }
}

function syncModelPathInputs(source = "model") {
  if (!llamaModelPathInput || !settingsLlamaModelPath) return;
  if (source === "settings") {
    llamaModelPathInput.value = settingsLlamaModelPath.value;
  } else {
    settingsLlamaModelPath.value = llamaModelPathInput.value;
  }
  syncSelectedGguf();
}

function favoritePayload() {
  const boxes = [...document.querySelectorAll("#favoriteModels input, #modelFavoriteModels input")];
  if (!boxes.length) return favoritePaths();
  const byPath = new Map();
  for (const box of boxes) byPath.set(box.value, box.checked || byPath.get(box.value) || false);
  const visible = new Set(byPath.keys());
  const preserved = favoritePaths().filter((path) => !visible.has(path));
  const checked = [...byPath.entries()].filter(([, isChecked]) => isChecked).map(([path]) => path);
  return [...new Set([...preserved, ...checked])];
}

function fillSettings(settings) {
  document.querySelector("#modelAdapter").value = settings.model_adapter;
  document.querySelector("#apiBase").value = settings.api_base;
  document.querySelector("#modelName").value = settings.model_name;
  if (ggufModelDirsCustom) ggufModelDirsCustom.value = settings.gguf_model_dirs_custom || "";
  if (llamaModelPathInput) llamaModelPathInput.value = settings.llama_model_path || "";
  if (settingsLlamaModelPath) settingsLlamaModelPath.value = settings.llama_model_path || "";
  document.querySelector("#llamaNCtx").value = settings.llama_n_ctx || 4096;
  document.querySelector("#settingsNCtx").value = settings.llama_n_ctx || 4096;
  document.querySelector("#llamaNThreads").value = settings.llama_n_threads || 8;
  document.querySelector("#llamaNGpuLayers").value = settings.llama_n_gpu_layers || 0;
  updateLoaderTuningControls(settings, stateCache?.system_scan || {});
  document.querySelector("#enableThinking").checked = Boolean(settings.enable_thinking);
  document.querySelector("#temperature").value = settings.temperature;
  document.querySelector("#topP").value = settings.top_p ?? 0.9;
  document.querySelector("#maxTokens").value = settings.max_tokens;
  document.querySelector("#maxTokensFromCtx").checked = Boolean(settings.max_tokens_from_ctx);
  document.querySelector("#historyLimit").value = settings.history_limit ?? 12;
  if (chatCompressorEnabled) chatCompressorEnabled.checked = settings.chat_compressor_enabled !== false;
  if (chatCompressorAutoTitle) chatCompressorAutoTitle.checked = settings.chat_compressor_auto_title !== false;
  if (chatCompressorPersistSummary) chatCompressorPersistSummary.checked = settings.chat_compressor_persist_summary !== false;
  if (chatCompressorTriggerTurns) chatCompressorTriggerTurns.value = settings.chat_compressor_trigger_turns ?? 10;
  if (chatCompressorKeepRecentTurns) chatCompressorKeepRecentTurns.value = settings.chat_compressor_keep_recent_turns ?? 6;
  if (chatCompressorThreshold) chatCompressorThreshold.value = settings.chat_compressor_context_threshold_tokens ?? 12000;
  if (chatCompressorMaxChars) chatCompressorMaxChars.value = settings.chat_compressor_max_summary_chars ?? 3500;
  if (chatCompressorDebug) chatCompressorDebug.checked = Boolean(settings.chat_compressor_debug);
  updateContextOptimizerControls(settings, stateCache);
  if (maatThinkingLevel) maatThinkingLevel.value = String(settings.maat_thinking_level || 0);
  updateSuperMemoryControls(settings, stateCache);
  updateSpiritControls(settings);
  updateStyleControls(settings);
  updateRewriteControls(settings, stateCache);
  updateCoreControls(settings, stateCache);
  updateRealityControls(settings, stateCache);
  updateBalanceControls(settings, stateCache);
  updateClaimGuardControls(settings, stateCache);
  updateAdaptiveLearningControls(settings, stateCache);
  updateFeedbackControls(settings, stateCache);
  updateProjectMemoryControls(settings, stateCache);
  updateFileBuilderControls(settings, stateCache);
  updateEmotionControls(settings);
  updateOfflineWikiControls(settings, stateCache);
  updateIdentityControls(settings, stateCache);
  updateEngineControls({ settings, maat_engine: stateCache?.maat_engine || {} });
  updateReflectionControls(settings, stateCache);
  updateAntiHalluControls(settings, stateCache);
  document.querySelector("#systemPrompt").value = settings.system_prompt || "";
  updateAdapterFields();
  syncSelectedGguf();
  renderFavoriteModels();
  renderChatFavoriteModels();
  updateThinkingControls();
  updateMaatThinkingControls();
  updateMaxTokenControls();
}

function updateAdapterFields() {
  const adapter = document.querySelector("#modelAdapter").value;
  document.querySelector("#apiSettings").hidden = adapter !== "openai_compat";
  document.querySelector("#llamaSettings").hidden = adapter !== "llama_cpp_direct";
  if (adapter === "llama_cpp_direct") {
    loadGgufModels(false);
  }
}

function syncSelectedGguf() {
  const select = document.querySelector("#llamaModelSelect");
  const path = llamaModelPathInput?.value || "";
  if (!select || !path) return;
  const hasOption = [...select.options].some((option) => option.value === path);
  select.value = hasOption ? path : "";
}

function renderGgufModels(payload) {
  const select = document.querySelector("#llamaModelSelect");
  const count = document.querySelector("#ggufModelCount");
  const currentPath = llamaModelPathInput?.value || "";
  ggufModelsCache = payload.models || [];
  select.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "GGUF-Modell auswählen...";
  select.appendChild(placeholder);

  const models = ggufModelsCache;
  for (const model of models) {
    const option = document.createElement("option");
    option.value = model.path;
    const size = model.size ? ` · ${formatBytes(model.size)}` : "";
    option.textContent = `${model.name}${size}`;
    option.title = model.path;
    select.appendChild(option);
  }

  const hasCurrentPath = currentPath && models.some((model) => model.path === currentPath);
  if (currentPath && !hasCurrentPath) {
    const custom = document.createElement("option");
    custom.value = currentPath;
    custom.textContent = `Aktueller manueller Pfad · ${shortPath(currentPath)}`;
    custom.title = currentPath;
    select.appendChild(custom);
  }
  syncSelectedGguf();

  const existingRoots = (payload.roots || []).filter((root) => root.exists).length;
  count.textContent = `${models.length} GGUF-Modelle gefunden · ${existingRoots} Modellordner aktiv`;
  renderFavoriteModels();
  renderChatFavoriteModels();
}

async function loadGgufModels(force = false) {
  if (ggufModelsLoaded && !force) return;
  const select = document.querySelector("#llamaModelSelect");
  const count = document.querySelector("#ggufModelCount");
  if (!select || !count) return;

  select.disabled = true;
  count.textContent = "Suche GGUF-Modelle...";
  try {
    const response = await fetch("/api/gguf-models");
    const data = await response.json();
    renderGgufModels(data);
    ggufModelsLoaded = true;
  } catch (error) {
    count.textContent = `GGUF-Suche fehlgeschlagen: ${error}`;
  } finally {
    select.disabled = false;
  }
}

async function loadState() {
  const response = await fetch("/api/state");
  stateCache = await response.json();
  renderRuntime(stateCache);
  renderPlugins(stateCache.plugins);
  fillSettings(stateCache.settings);
  updateEngineControls(stateCache);
  setConfigurationLocked(isSending);
  statusLine.textContent = describeModel(stateCache.settings);
  await loadChats();
  await loadPersonGraph(stateCache.settings?.supermem_current_user || "User");
}

async function saveSettings(statusElement = null) {
  if (isSending) {
    if (statusElement) flashSavedStatus(statusElement, "Stream läuft");
    statusLine.textContent = "Settings sind während des Streamings gesperrt.";
    return null;
  }
  const payload = {
    model_adapter: document.querySelector("#modelAdapter").value,
    api_base: document.querySelector("#apiBase").value.trim(),
    model_name: document.querySelector("#modelName").value.trim(),
    loader_tuning_mode: stateCache?.settings?.loader_tuning_mode === "auto" ? "auto" : "manual",
    gguf_model_dirs_custom: ggufModelDirsCustom?.value?.trim() || "",
    llama_model_path: (llamaModelPathInput?.value || settingsLlamaModelPath?.value || "").trim(),
    llama_n_ctx: Number(document.querySelector("#llamaNCtx").value),
    llama_n_threads: Number(document.querySelector("#llamaNThreads").value),
    llama_n_gpu_layers: Number(document.querySelector("#llamaNGpuLayers").value),
    favorite_model_paths: favoritePayload(),
    enable_thinking: document.querySelector("#enableThinking").checked,
    temperature: Number(document.querySelector("#temperature").value),
    top_p: Number(document.querySelector("#topP").value),
    max_tokens: Number(document.querySelector("#maxTokens").value),
    max_tokens_from_ctx: document.querySelector("#maxTokensFromCtx").checked,
    history_limit: Number(document.querySelector("#historyLimit").value),
    chat_compressor_enabled: chatCompressorEnabled?.checked !== false,
    chat_compressor_auto_title: chatCompressorAutoTitle?.checked !== false,
    chat_compressor_persist_summary: chatCompressorPersistSummary?.checked !== false,
    chat_compressor_trigger_turns: Number(chatCompressorTriggerTurns?.value || 10),
    chat_compressor_keep_recent_turns: Number(chatCompressorKeepRecentTurns?.value || 6),
    chat_compressor_context_threshold_tokens: Number(chatCompressorThreshold?.value || 12000),
    chat_compressor_max_summary_chars: Number(chatCompressorMaxChars?.value || 3500),
    chat_compressor_debug: Boolean(chatCompressorDebug?.checked),
    context_optimizer_enabled: contextOptimizerEnabled?.checked !== false,
    context_optimizer_debug: Boolean(contextOptimizerDebug?.checked),
    context_optimizer_current_user_block: contextOptimizerUserBlock?.checked !== false,
    context_optimizer_max_memory_items: Number(contextOptimizerMaxMemoryItems?.value || 6),
    context_optimizer_max_memory_chars: Number(contextOptimizerMaxMemoryChars?.value || 2600),
    maat_thinking_level: Number(maatThinkingLevel?.value || stateCache?.settings?.maat_thinking_level || 0),
    supermem_enabled: supermemEnabled?.checked !== false,
    supermem_autostore: supermemAutostore?.checked !== false,
    supermem_autorecall: supermemAutorecall?.checked !== false,
    supermem_debug: Boolean(supermemDebug?.checked),
    supermem_allow_model_saves: supermemModelSaves?.checked !== false,
    supermem_show_save_box: supermemSaveBox?.checked !== false,
    supermem_dreaming_enabled: supermemDreaming?.checked !== false,
    supermem_dream_on_load: Boolean(supermemDreamOnLoad?.checked),
    supermem_dream_hours: Number(supermemDreamHours?.value || 24),
    supermem_archive_enabled: supermemArchive?.checked !== false,
    supermem_archive_after_days: Number(supermemArchiveDays?.value || 30),
    supermem_person_recall: supermemPersonRecall?.checked !== false,
    supermem_person_graph: supermemPersonGraph?.checked !== false,
    supermem_current_user: selectedMemoryUser(),
    supermem_top_k: Number(supermemTopK?.value || 5),
    supermem_min_score: Number(supermemMinScore?.value || 0.15),
    supermem_person_top_k: Number(supermemPersonTopK?.value || 4),
    supermem_person_graph_top_k: Number(supermemGraphTopK?.value || 2),
    supermem_user_memory_bonus: Number(supermemUserBonus?.value || 0.12),
    supermem_max_memories: Number(supermemMaxMemories?.value || 1000),
    supermem_known_users: knownUsersFromSettings({
      ...(stateCache?.settings || {}),
      supermem_known_users: supermemKnownUsers?.value || "",
      supermem_current_user: selectedMemoryUser(),
    }).join(", "),
    supermem_person_names: splitLooseList(supermemPersonNames?.value || "").join(", "),
    supermem_person_ambiguous_names: splitLooseList(supermemAmbiguousNames?.value || "").join(", "),
    spirit_enabled: Boolean(spiritEnabled?.checked),
    spirit_mode: spiritMode?.value || "standard",
    spirit_language: spiritLanguage?.value || "auto",
    spirit_once: spiritOnce?.checked !== false,
    spirit_use_emojis: spiritUseEmojis?.checked !== false,
    style_enabled: styleEnabled?.checked !== false,
    style_debug: Boolean(styleDebug?.checked),
    style_greeting_override: styleGreetingOverride?.checked !== false,
    style_tone_auto: styleToneAuto?.checked !== false,
    style_tone_mode: styleToneMode?.value || "friendly",
    style_opening_mode: styleOpeningMode?.value || "varied",
    style_density_mode: styleDensityMode?.value || "normal",
    style_heading_mode: styleHeadingMode?.value || "simple",
    style_list_mode: styleListMode?.value || "auto",
    style_emoji_mode: styleEmojiMode?.value || "few",
    style_old_smiley_mode: styleOldSmileyMode?.value || "none",
    rewrite_enabled: rewriteEnabled?.checked !== false,
    rewrite_trim_outputs: Boolean(rewriteTrimOutputs?.checked),
    rewrite_show_banner: Boolean(rewriteShowBanner?.checked),
    rewrite_mode: rewriteMode?.value || "light",
    rewrite_field_weak: Number(rewriteFieldWeak?.value || 6.2),
    rewrite_field_strong: Number(rewriteFieldStrong?.value || 5.0),
    rewrite_r_min: Number(rewriteRMin?.value || 7.0),
    maat_core_enabled: coreEnabled?.checked !== false,
    maat_core_mode: coreMode?.value || "standard",
    reality_enabled: realityEnabled?.checked !== false,
    reality_inject_time: realityInjectTime?.checked !== false,
    reality_show_banner: Boolean(realityShowBanner?.checked),
    balance_enabled: balanceEnabled?.checked !== false,
    balance_debug: Boolean(balanceDebug?.checked),
    balance_once: Boolean(balanceOnce?.checked),
    balance_self_reflect: balanceSelfReflect?.checked !== false,
    balance_dynamic: balanceDynamic?.checked !== false,
    balance_context_weights: balanceContextWeights?.checked !== false,
    balance_counterpart_mode: balanceCounterpartMode?.checked !== false,
    balance_level: balanceLevel?.value || "standard",
    claim_guard_enabled: claimGuardEnabled?.checked !== false,
    claim_guard_after_output: claimGuardAfterOutput?.checked !== false,
    claim_guard_show_banner: Boolean(claimGuardBanner?.checked),
    claim_guard_mode: claimGuardMode?.value || "balanced",
    adaptive_learning_enabled: adaptiveLearningEnabled?.checked !== false,
    adaptive_learning_inject: adaptiveLearningInject?.checked !== false,
    adaptive_learning_debug: Boolean(adaptiveLearningDebug?.checked),
    adaptive_learning_per_turn: Number(adaptiveLearningPerTurn?.value || 2),
    adaptive_learning_exploration_rate: Number(adaptiveLearningExplore?.value || 0.25),
    adaptive_learning_user_bonus: Number(adaptiveLearningUserBonus?.value || 0.2),
    feedback_enabled: feedbackEnabled?.checked !== false,
    feedback_debug: Boolean(feedbackDebug?.checked),
    feedback_self_learning_enabled: feedbackSelfLearning?.checked !== false,
    feedback_history_limit: Number(feedbackHistoryLimit?.value || 25),
    feedback_warn_below_b: Number(feedbackWarnB?.value || 0.6),
    feedback_warn_below_r: Number(feedbackWarnR?.value || 0.75),
    feedback_warn_below_h: Number(feedbackWarnH?.value || 0.65),
    feedback_self_learning_per_report: Number(feedbackSelfPerReport?.value || 2),
    project_memory_enabled: projectMemoryEnabled?.checked !== false,
    project_memory_debug: Boolean(projectMemoryDebug?.checked),
    project_memory_top_k: Number(projectMemoryTopK?.value || 2),
    project_memory_max_chars: Number(projectMemoryMaxChars?.value || 2600),
    file_builder_enabled: fileBuilderEnabled?.checked !== false,
    file_builder_inject_instructions: fileBuilderInject?.checked !== false,
    file_builder_replace_blocks: fileBuilderReplace?.checked !== false,
    file_builder_show_source_code: fileBuilderSource?.checked !== false,
    file_builder_auto_capture_fences: fileBuilderFences?.checked !== false,
    file_builder_compile_tex_pdf: fileBuilderCompileTex?.checked !== false,
    file_builder_python_syntax_check: fileBuilderPythonCheck?.checked !== false,
    file_builder_python_run_enabled: fileBuilderPythonRun?.checked !== false,
    file_builder_python_run_in_terminal: fileBuilderTerminal?.checked !== false,
    file_builder_inject_feedback: fileBuilderFeedback?.checked !== false,
    file_builder_debug: Boolean(fileBuilderDebug?.checked),
    file_builder_preview_chars: Number(fileBuilderPreviewChars?.value || 5000),
    emotion_enabled: emotionEnabled?.checked !== false,
    emotion_debug: Boolean(emotionDebug?.checked),
    emotion_mode: emotionMode?.value || "full",
    emotion_language: emotionLanguage?.value || "auto",
    offline_wiki_enabled: Boolean(offlineWikiEnabled?.checked),
    offline_wiki_auto: offlineWikiAuto?.checked !== false,
    offline_wiki_debug: Boolean(offlineWikiDebug?.checked),
    offline_wiki_log: offlineWikiLog?.checked !== false,
    offline_wiki_zim_path: offlineWikiPath?.value?.trim() || "",
    offline_wiki_max_chars: Number(offlineWikiMaxChars?.value || 1400),
    offline_wiki_multi_max_chars: Number(offlineWikiMultiMaxChars?.value || 700),
    offline_wiki_max_terms: Number(offlineWikiMaxTerms?.value || 2),
    identity_enabled: identityEnabled?.checked !== false,
    identity_once: identityOnce?.checked !== false,
    identity_name: identityName?.value?.trim() || "MAAT-KI",
    identity_mode: identityMode?.value || "balanced",
    engine_enabled: engineEnabled?.checked !== false,
    engine_show_in_chat: Boolean(engineShowInChat?.checked),
    engine_show_cci_debug: Boolean(engineShowCciDebug?.checked),
    advanced_cci_enabled: advancedCciEnabled?.checked !== false,
    advanced_cci_show_debug: Boolean(advancedCciShowDebug?.checked),
    advanced_cci_kappa: Number(advancedCciKappa?.value || 0.5),
    reflection_enabled: reflectionEnabled?.checked !== false,
    reflection_banner: Boolean(reflectionBanner?.checked),
    reflection_prompt_rule: reflectionPromptRule?.checked !== false,
    reflection_mode: reflectionMode?.value || "auto",
    antihallu_enabled: antihalluEnabled?.checked !== false,
    antihallu_show_banner: Boolean(antihalluBanner?.checked),
    antihallu_gap_questions: antihalluGaps?.checked !== false,
    antihallu_symbolic_lenient: antihalluSymbolic?.checked !== false,
    antihallu_mode: antihalluMode?.value || "soften",
    antihallu_soften_threshold: Number(antihalluSoftenThreshold?.value || 0.55),
    antihallu_strict_threshold: Number(antihalluStrictThreshold?.value || 0.85),
    system_prompt: document.querySelector("#systemPrompt").value,
  };
  const response = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  stateCache.settings = data.settings;
  if (data.system_scan) stateCache.system_scan = data.system_scan;
  if (data.offline_wiki) stateCache.offline_wiki = data.offline_wiki;
  fillSettings(data.settings);
  renderFavoriteModels();
  renderChatFavoriteModels();
  updateSuperMemoryControls(data.settings, stateCache);
  updateSpiritControls(data.settings);
  updateStyleControls(data.settings);
  if (data.maat_rewrite) stateCache.maat_rewrite = data.maat_rewrite;
  updateRewriteControls(data.settings, stateCache);
  if (data.maat_core) stateCache.maat_core = data.maat_core;
  updateCoreControls(data.settings, stateCache);
  if (data.maat_reality) stateCache.maat_reality = data.maat_reality;
  updateRealityControls(data.settings, stateCache);
  if (data.maat_balance) stateCache.maat_balance = data.maat_balance;
  updateBalanceControls(data.settings, stateCache);
  if (data.maat_claim_guard) stateCache.maat_claim_guard = data.maat_claim_guard;
  updateClaimGuardControls(data.settings, stateCache);
  if (data.maat_adaptive_learning) stateCache.maat_adaptive_learning = data.maat_adaptive_learning;
  updateAdaptiveLearningControls(data.settings, stateCache);
  if (data.maat_feedback_tool) stateCache.maat_feedback_tool = data.maat_feedback_tool;
  updateFeedbackControls(data.settings, stateCache);
  if (data.maat_project_memory) stateCache.maat_project_memory = data.maat_project_memory;
  updateProjectMemoryControls(data.settings, stateCache);
  if (data.maat_file_builder) stateCache.maat_file_builder = data.maat_file_builder;
  updateFileBuilderControls(data.settings, stateCache);
  updateEmotionControls(data.settings);
  updateOfflineWikiControls(data.settings, stateCache);
  if (data.maat_identity) stateCache.maat_identity = data.maat_identity;
  updateIdentityControls(data.settings, stateCache);
  updateEngineControls({ settings: data.settings, maat_engine: stateCache.maat_engine || {} });
  updateReflectionControls(data.settings, stateCache);
  if (data.maat_antihallu) stateCache.maat_antihallu = data.maat_antihallu;
  updateAntiHalluControls(data.settings, stateCache);
  updateLoaderTuningControls(data.settings, stateCache.system_scan || {});
  setConfigurationLocked(isSending);
  statusLine.textContent = "Einstellungen gespeichert";
  flashSavedStatus(statusElement);
}

async function savePromptSettings() {
  await saveSettings(savePromptStatus);
  statusLine.textContent = "Systemprompt gespeichert";
}

function parseSseEvents(buffer) {
  const events = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  for (const part of parts) {
    let event = "message";
    let data = "";
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (data) {
      try {
        events.push({ event, data: JSON.parse(data) });
      } catch {
        events.push({ event, data: { content: data } });
      }
    }
  }
  return { events, rest };
}

async function sendMessage(text) {
  if (isSending) return;
  isSending = true;
  setConfigurationLocked(true);
  const startedChatId = currentChatId;
  addMessage("user", text);
  const assistant = addMessage("assistant", "");
  const streamState = {
    chatId: startedChatId,
    content: "",
    assistantElement: assistant,
    progressOptions: null,
    fileBuilderCards: [],
    done: false,
    stopped: false,
  };
  const abortController = new AbortController();
  currentAbortController = abortController;
  registerStream(streamState);
  const initialProgress = {
    title: "MAAT verarbeitet den Kontext",
    tokens: estimateProgressTokens(text),
    status: "Prompt wird vorbereitet",
    detail: "Die Antwort startet gleich. Diese Anzeige wird automatisch ersetzt.",
    kind: "prompt",
  };
  streamState.progressOptions = initialProgress;
  setProgressCard(assistant, initialProgress);
  addLogEntry({
    source: "chat",
    title: "Stream gestartet",
    lines: [`User ${selectedMemoryUser()}: ${trimPreview(text, 140)}`],
  });
  statusLine.textContent = "MAAT denkt und streamt...";
  setSendButtonStreaming(true);

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, chat_id: currentChatId }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    if (!response.body) {
      renderMessageContent(assistant, "Streaming wird von diesem Browser nicht unterstützt.");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSseEvents(buffer);
      buffer = parsed.rest;
      for (const item of parsed.events) {
        if (item.event === "token") {
          appendStreamToken(streamState, item.data.content || "");
        } else if (item.event === "replace") {
          updateStreamContent(streamState, item.data.content || "");
        } else if (item.event === "meta") {
          if (item.data.chat_id != null) {
            updateStreamChatId(streamState, item.data.chat_id);
          }
          addLogEntry({
            source: "stream",
            title: "Stream Meta",
            lines: [
              `chat_id=${item.data.chat_id ?? ""}`,
              `plugins=${Array.isArray(item.data.plugins) ? item.data.plugins.length : 0}`,
            ],
          });
        } else if (item.event === "done") {
          if (item.data.chat_id != null) {
            updateStreamChatId(streamState, item.data.chat_id);
          }
          streamState.done = true;
          window.setTimeout(() => {
            const key = streamKey(streamState.chatId);
            if (activeStreams.get(key) === streamState) {
              activeStreams.delete(key);
            }
          }, 60000);
          addLogEntry({
            source: "chat",
            title: "Stream fertig",
            lines: [`chat_id=${streamState.chatId ?? currentChatId ?? ""}`],
          });
        } else if (item.event === "maat") {
          statusLine.textContent = `MAAT Score: ${JSON.stringify(item.data)}`;
        } else if (item.event === "maat_reality") {
          stateCache = stateCache || {};
          stateCache.maat_reality = {
            ...(stateCache.maat_reality || {}),
            last_eval: item.data,
          };
          updateRealityControls(stateCache.settings || {}, stateCache);
          addLogEntry({
            source: "reality",
            title: "MAAT Reality",
            lines: [
              item.data.direct ? "direct=true" : "direct=false",
              `question=${trimPreview(item.data.question || "", 120)}`,
              `answer=${trimPreview(item.data.answer || "", 120)}`,
            ],
          });
        } else if (item.event === "maat_engine") {
          stateCache = stateCache || {};
          stateCache.maat_engine = {
            ...(stateCache.maat_engine || {}),
            last_eval: item.data,
          };
          updateEngineControls(stateCache);
        } else if (item.event === "maat_cci") {
          stateCache = stateCache || {};
          stateCache.maat_cci = {
            ...(stateCache.maat_cci || {}),
            last_eval: item.data,
          };
          updateEngineControls(stateCache);
        } else if (item.event === "maat_reflection") {
          stateCache = stateCache || {};
          stateCache.maat_reflection = {
            ...(stateCache.maat_reflection || {}),
            last_eval: item.data,
          };
          updateReflectionControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_rewrite") {
          stateCache = stateCache || {};
          stateCache.maat_rewrite = {
            ...(stateCache.maat_rewrite || {}),
            last_eval: item.data,
          };
          updateRewriteControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_balance") {
          stateCache = stateCache || {};
          stateCache.maat_balance = {
            ...(stateCache.maat_balance || {}),
            last_eval: item.data,
          };
          updateBalanceControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_claim_guard") {
          stateCache = stateCache || {};
          stateCache.maat_claim_guard = {
            ...(stateCache.maat_claim_guard || {}),
            last_eval: item.data,
          };
          updateClaimGuardControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_adaptive_learning") {
          stateCache = stateCache || {};
          stateCache.maat_adaptive_learning = {
            ...(stateCache.maat_adaptive_learning || {}),
            last_why: item.data,
          };
          updateAdaptiveLearningControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_adaptive_learning_after") {
          stateCache = stateCache || {};
          stateCache.maat_adaptive_learning = {
            ...(stateCache.maat_adaptive_learning || {}),
            last_feedback: item.data,
          };
          updateAdaptiveLearningControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_feedback_tool") {
          stateCache = stateCache || {};
          stateCache.maat_feedback_tool = {
            ...(stateCache.maat_feedback_tool || {}),
            ...item.data,
          };
          updateFeedbackControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_project_memory") {
          stateCache = stateCache || {};
          stateCache.maat_project_memory = {
            ...(stateCache.maat_project_memory || {}),
            last_recall: item.data,
          };
          updateProjectMemoryControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "maat_file_builder") {
          stateCache = stateCache || {};
          stateCache.maat_file_builder = {
            ...(stateCache.maat_file_builder || {}),
            ...item.data,
          };
          streamState.fileBuilderCards.push(item.data);
          if (isViewingStream(streamState)) {
            appendFileBuilderChatCard(ensureStreamAssistantElement(streamState), item.data);
          }
          addLogEntry({
            source: "docs",
            title: "MAAT Docs/File Builder",
            lines: [
              `records=${Array.isArray(item.data.records) ? item.data.records.length : 0}`,
              ...(item.data.records || []).slice(0, 3).map((record) => `${record.filename} · ${record.relative_path || ""}`),
              ...(item.data.errors || []).slice(0, 2).map((error) => `ERR: ${error}`),
            ],
          });
          docsLoaded = false;
          if (chatDocsEl && !chatDocsEl.hidden) loadDocsPanel(true);
        } else if (item.event === "maat_chat_compressor") {
          stateCache = stateCache || {};
          stateCache.maat_chat_compressor = item.data;
        } else if (item.event === "maat_chat_digest") {
          stateCache = stateCache || {};
          stateCache.maat_chat_digest = item.data;
          addLogEntry({
            source: "compressor",
            title: "MAAT Chat Digest",
            lines: [
              `title=${item.data.title || "-"}`,
              `messages=${item.data.message_count ?? 0} summary_chars=${item.data.summary_chars ?? 0}`,
              `summary=${trimPreview(item.data.summary_short || "", 180)}`,
            ],
          });
        } else if (item.event === "maat_antihallu") {
          stateCache = stateCache || {};
          stateCache.maat_antihallu = {
            ...(stateCache.maat_antihallu || {}),
            last_eval: item.data,
          };
          updateAntiHalluControls(stateCache.settings || {}, stateCache);
        } else if (item.event === "log") {
          const progressOptions = progressOptionsFromLog(item.data);
          if (progressOptions) updateStreamProgress(streamState, progressOptions);
          if (isViewingStream(streamState)) {
            maybeUpdateModelProgress(ensureStreamAssistantElement(streamState), item.data);
          }
          addLogEntry(item.data);
        }
        if (isSending) setConfigurationLocked(true);
        if (isViewingStream(streamState)) scrollMessagesToBottom();
      }
    }

    statusLine.textContent = "Bereit";
  } catch (error) {
    if (error?.name === "AbortError") {
      streamState.done = true;
      streamState.stopped = true;
      addLogEntry({
        source: "chat",
        title: "Stream gestoppt",
        lines: [`chat_id=${streamState.chatId ?? currentChatId ?? ""}`],
      });
      if (!streamState.content) {
        updateStreamContent(streamState, "Antwort gestoppt.");
      } else if (isViewingStream(streamState)) {
        renderStreamState(streamState);
      }
      statusLine.textContent = "Antwort gestoppt";
      window.setTimeout(() => {
        const key = streamKey(streamState.chatId);
        if (activeStreams.get(key) === streamState) {
          activeStreams.delete(key);
        }
      }, 600000);
      return;
    }
    console.error("Chat stream failed", error);
    addLogEntry({
      source: "error",
      title: "Stream Fehler",
      lines: [String(error.message || error)],
    });
    updateStreamContent(streamState, `Fehler beim Senden: ${error.message || error}`);
    statusLine.textContent = "Fehler beim Senden";
  } finally {
    if (currentAbortController === abortController) {
      currentAbortController = null;
    }
    setSendButtonStreaming(false);
    isSending = false;
    try {
      await loadState();
      renderChatList();
    } catch (error) {
      console.warn("State refresh failed after chat stream", error);
      statusLine.textContent = "Antwort fertig · Status-Refresh fehlgeschlagen";
    } finally {
      setConfigurationLocked(false);
    }
  }
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSending || inputIsComposing) return;
  const typedText = input.value.trim();
  if (!typedText && pendingAttachments.length === 0) return;
  if (/^\^+$/.test(typedText) && pendingAttachments.length === 0) {
    input.value = "";
    statusLine.textContent = "Dead-Key-Rest verworfen";
    return;
  }
  const text = buildOutgoingMessage(typedText);
  input.value = "";
  clearPendingAttachments();
  await sendMessage(text);
});

input.addEventListener("keydown", (event) => {
  if (event.isComposing || inputIsComposing || event.keyCode === 229) return;
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (isSending) return;
    composer.requestSubmit();
  }
});

input.addEventListener("compositionstart", () => {
  inputIsComposing = true;
});

input.addEventListener("compositionend", () => {
  inputIsComposing = false;
});

input.addEventListener("paste", (event) => {
  const pastedText = event.clipboardData?.getData("text/plain") || "";
  if (!shouldCreatePasteAttachment(pastedText)) return;
  event.preventDefault();
  addPendingTextAttachment(pastedText);
  statusLine.textContent = `Text als Anhang vorbereitet · ${formatBytes(textByteLength(pastedText))}`;
});

document.querySelector("#reloadState").addEventListener("click", loadState);
chatViewChat?.addEventListener("click", () => setChatView("chat"));
chatViewLog?.addEventListener("click", () => setChatView("log"));
chatViewHelp?.addEventListener("click", () => setChatView("help"));
chatViewProjects?.addEventListener("click", () => setChatView("projects"));
chatViewDocs?.addEventListener("click", () => setChatView("docs"));
document.querySelector("#saveSettings").addEventListener("click", () => saveSettings(saveSettingsStatus));
document.querySelector("#saveModelSettings").addEventListener("click", () => saveSettings(saveModelStatus));
restartWebCore?.addEventListener("click", restartMaatWebCore);
loaderAutoMode?.addEventListener("click", () => setLoaderTuningMode("auto"));
loaderManualMode?.addEventListener("click", () => setLoaderTuningMode("manual"));
runSystemScan?.addEventListener("click", applySystemScan);
document.querySelector("#savePromptSettings").addEventListener("click", savePromptSettings);
document.querySelector("#saveMaatSettings").addEventListener("click", async () => {
  await saveSettings(saveMaatStatus);
});
themeModeSelect?.addEventListener("change", () => {
  const mode = normalizeThemeMode(themeModeSelect.value);
  localStorage.setItem(THEME_STORAGE_KEY, mode);
  applyThemeMode(mode, true);
});
document.querySelector("#modelAdapter").addEventListener("change", updateAdapterFields);
document.querySelector("#enableThinking").addEventListener("change", async () => {
  await saveThinkingSetting(document.querySelector("#enableThinking").checked);
});
document.querySelector("#maxTokensFromCtx").addEventListener("change", updateMaxTokenControls);
maatThinkingLevel?.addEventListener("change", async (event) => {
  await setMaatThinkingLevel(Number(event.target.value));
});
maatThinkingLevel?.addEventListener("input", (event) => {
  previewMaatThinkingLevel(Number(event.target.value));
});
maatThinkSlider?.addEventListener("change", async (event) => {
  await setMaatThinkingLevel(Number(event.target.value));
});
maatThinkSlider?.addEventListener("input", (event) => {
  previewMaatThinkingLevel(Number(event.target.value));
});
maatThinkOff?.addEventListener("click", async () => {
  await setMaatThinkingLevel(0);
});
maatThinkingOff?.addEventListener("click", async () => {
  await setMaatThinkingLevel(0);
});
for (const control of [
  contextOptimizerEnabled,
  contextOptimizerDebug,
  contextOptimizerUserBlock,
  contextOptimizerMaxMemoryItems,
  contextOptimizerMaxMemoryChars,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.context_optimizer_enabled = contextOptimizerEnabled?.checked !== false;
    stateCache.settings.context_optimizer_debug = Boolean(contextOptimizerDebug?.checked);
    stateCache.settings.context_optimizer_current_user_block = contextOptimizerUserBlock?.checked !== false;
    stateCache.settings.context_optimizer_max_memory_items = Number(contextOptimizerMaxMemoryItems?.value || 6);
    stateCache.settings.context_optimizer_max_memory_chars = Number(contextOptimizerMaxMemoryChars?.value || 2600);
    updateContextOptimizerControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [spiritEnabled, spiritMode, spiritLanguage, spiritOnce, spiritUseEmojis]) {
  control?.addEventListener("change", () => {
    if (!stateCache?.settings) return;
    stateCache.settings.spirit_enabled = Boolean(spiritEnabled?.checked);
    stateCache.settings.spirit_mode = spiritMode?.value || "standard";
    stateCache.settings.spirit_language = spiritLanguage?.value || "auto";
    stateCache.settings.spirit_once = spiritOnce?.checked !== false;
    stateCache.settings.spirit_use_emojis = spiritUseEmojis?.checked !== false;
    updateSpiritControls(stateCache.settings);
  });
}
for (const control of [
  supermemEnabled,
  supermemAutostore,
  supermemAutorecall,
  supermemDebug,
  supermemModelSaves,
  supermemSaveBox,
  supermemDreaming,
  supermemDreamOnLoad,
  supermemArchive,
  supermemPersonRecall,
  supermemPersonGraph,
  supermemTopK,
  supermemMinScore,
  supermemGraphTopK,
  supermemPersonTopK,
  supermemUserBonus,
  supermemMaxMemories,
  supermemDreamHours,
  supermemArchiveDays,
  supermemKnownUsers,
  supermemPersonNames,
  supermemAmbiguousNames,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.supermem_enabled = supermemEnabled?.checked !== false;
    stateCache.settings.supermem_autostore = supermemAutostore?.checked !== false;
    stateCache.settings.supermem_autorecall = supermemAutorecall?.checked !== false;
    stateCache.settings.supermem_debug = Boolean(supermemDebug?.checked);
    stateCache.settings.supermem_allow_model_saves = supermemModelSaves?.checked !== false;
    stateCache.settings.supermem_show_save_box = supermemSaveBox?.checked !== false;
    stateCache.settings.supermem_dreaming_enabled = supermemDreaming?.checked !== false;
    stateCache.settings.supermem_dream_on_load = Boolean(supermemDreamOnLoad?.checked);
    stateCache.settings.supermem_archive_enabled = supermemArchive?.checked !== false;
    stateCache.settings.supermem_person_recall = supermemPersonRecall?.checked !== false;
    stateCache.settings.supermem_person_graph = supermemPersonGraph?.checked !== false;
    stateCache.settings.supermem_current_user = selectedMemoryUser();
    stateCache.settings.supermem_top_k = Number(supermemTopK?.value || 5);
    stateCache.settings.supermem_min_score = Number(supermemMinScore?.value || 0.15);
    stateCache.settings.supermem_person_top_k = Number(supermemPersonTopK?.value || 4);
    stateCache.settings.supermem_person_graph_top_k = Number(supermemGraphTopK?.value || 2);
    stateCache.settings.supermem_user_memory_bonus = Number(supermemUserBonus?.value || 0.12);
    stateCache.settings.supermem_max_memories = Number(supermemMaxMemories?.value || 1000);
    stateCache.settings.supermem_dream_hours = Number(supermemDreamHours?.value || 24);
    stateCache.settings.supermem_archive_after_days = Number(supermemArchiveDays?.value || 30);
    stateCache.settings.supermem_known_users = knownUsersFromSettings({
      ...stateCache.settings,
      supermem_known_users: supermemKnownUsers?.value || "",
      supermem_current_user: selectedMemoryUser(),
    }).join(", ");
    stateCache.settings.supermem_person_names = splitLooseList(supermemPersonNames?.value || "").join(", ");
    stateCache.settings.supermem_person_ambiguous_names = splitLooseList(supermemAmbiguousNames?.value || "").join(", ");
    updateSuperMemoryControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}

async function applyCurrentMemoryUser(name) {
  const user = normalizeUserName(name);
  if (!user || !stateCache?.settings) return;
  const users = knownUsersFromSettings({
    ...stateCache.settings,
    supermem_known_users: supermemKnownUsers?.value || stateCache.settings.supermem_known_users || "",
    supermem_current_user: user,
  });
  stateCache.settings.supermem_current_user = user;
  stateCache.settings.supermem_known_users = users.join(", ");
  updateSuperMemoryControls(stateCache.settings, stateCache);
  await saveSettings();
  await loadPersonGraph(user);
}

chatCurrentUser?.addEventListener("change", async () => {
  await applyCurrentMemoryUser(chatCurrentUser.value);
});

supermemCurrentUser?.addEventListener("change", async () => {
  await applyCurrentMemoryUser(supermemCurrentUser.value);
});

supermemAddUser?.addEventListener("click", async () => {
  const user = normalizeUserName(supermemNewUser?.value || "");
  if (!user) return;
  if (supermemNewUser) supermemNewUser.value = "";
  await applyCurrentMemoryUser(user);
});

supermemNewUser?.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  supermemAddUser?.click();
});

personGraphRefresh?.addEventListener("click", async () => {
  await loadPersonGraph(personGraphSelectedUser());
});

personGraphNew?.addEventListener("click", () => {
  blankPersonGraphForm();
});

personGraphSourceUser?.addEventListener("change", async () => {
  await loadPersonGraph(personGraphSelectedUser());
});

personGraphSelect?.addEventListener("change", () => {
  const selected = personGraphCache.entries.find((entry) => String(entry.id) === String(personGraphSelect.value || ""));
  fillPersonGraphForm(selected || null);
});

personGraphSave?.addEventListener("click", async () => {
  await savePersonGraphEntry();
});

personGraphDelete?.addEventListener("click", async () => {
  await deletePersonGraphEntry();
});

supermemRunDream?.addEventListener("click", async () => {
  if (!supermemDreamStatus) return;
  supermemDreamStatus.dataset.busy = "1";
  supermemDreamStatus.textContent = "Dreaming läuft...";
  supermemRunDream.disabled = true;
  try {
    await saveSettings();
    const response = await fetch("/api/super-memory/dream", { method: "POST" });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "Dreaming fehlgeschlagen");
    if (data.settings) stateCache.settings = data.settings;
    if (data.super_memory) stateCache.super_memory = data.super_memory;
    const result = data.result || {};
    supermemDreamStatus.textContent = `Dream fertig · Dreams ${result.created || 0}+${result.updated || 0} · Archiv ${result.archive?.archived || 0}`;
    updateSuperMemoryControls(stateCache.settings, stateCache);
  } catch (error) {
    supermemDreamStatus.textContent = `Dream Fehler: ${error.message}`;
  } finally {
    delete supermemDreamStatus.dataset.busy;
    supermemRunDream.disabled = false;
  }
});

for (const control of [
  styleEnabled,
  styleDebug,
  styleGreetingOverride,
  styleToneAuto,
  styleToneMode,
  styleOpeningMode,
  styleDensityMode,
  styleHeadingMode,
  styleListMode,
  styleEmojiMode,
  styleOldSmileyMode,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.style_enabled = styleEnabled?.checked !== false;
    stateCache.settings.style_debug = Boolean(styleDebug?.checked);
    stateCache.settings.style_greeting_override = styleGreetingOverride?.checked !== false;
    stateCache.settings.style_tone_auto = styleToneAuto?.checked !== false;
    stateCache.settings.style_tone_mode = styleToneMode?.value || "friendly";
    stateCache.settings.style_opening_mode = styleOpeningMode?.value || "varied";
    stateCache.settings.style_density_mode = styleDensityMode?.value || "normal";
    stateCache.settings.style_heading_mode = styleHeadingMode?.value || "simple";
    stateCache.settings.style_list_mode = styleListMode?.value || "auto";
    stateCache.settings.style_emoji_mode = styleEmojiMode?.value || "few";
    stateCache.settings.style_old_smiley_mode = styleOldSmileyMode?.value || "none";
    updateStyleControls(stateCache.settings);
    await saveSettings();
  });
}
for (const control of [
  rewriteEnabled,
  rewriteTrimOutputs,
  rewriteShowBanner,
  rewriteMode,
  rewriteFieldWeak,
  rewriteFieldStrong,
  rewriteRMin,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.rewrite_enabled = rewriteEnabled?.checked !== false;
    stateCache.settings.rewrite_trim_outputs = Boolean(rewriteTrimOutputs?.checked);
    stateCache.settings.rewrite_show_banner = Boolean(rewriteShowBanner?.checked);
    stateCache.settings.rewrite_mode = rewriteMode?.value || "light";
    stateCache.settings.rewrite_field_weak = Number(rewriteFieldWeak?.value || 6.2);
    stateCache.settings.rewrite_field_strong = Number(rewriteFieldStrong?.value || 5.0);
    stateCache.settings.rewrite_r_min = Number(rewriteRMin?.value || 7.0);
    updateRewriteControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [coreEnabled, coreMode]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.maat_core_enabled = coreEnabled?.checked !== false;
    stateCache.settings.maat_core_mode = coreMode?.value || "standard";
    updateCoreControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [realityEnabled, realityInjectTime, realityShowBanner]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.reality_enabled = realityEnabled?.checked !== false;
    stateCache.settings.reality_inject_time = realityInjectTime?.checked !== false;
    stateCache.settings.reality_show_banner = Boolean(realityShowBanner?.checked);
    updateRealityControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [
  balanceEnabled,
  balanceDebug,
  balanceOnce,
  balanceSelfReflect,
  balanceDynamic,
  balanceContextWeights,
  balanceCounterpartMode,
  balanceLevel,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.balance_enabled = balanceEnabled?.checked !== false;
    stateCache.settings.balance_debug = Boolean(balanceDebug?.checked);
    stateCache.settings.balance_once = Boolean(balanceOnce?.checked);
    stateCache.settings.balance_self_reflect = balanceSelfReflect?.checked !== false;
    stateCache.settings.balance_dynamic = balanceDynamic?.checked !== false;
    stateCache.settings.balance_context_weights = balanceContextWeights?.checked !== false;
    stateCache.settings.balance_counterpart_mode = balanceCounterpartMode?.checked !== false;
    stateCache.settings.balance_level = balanceLevel?.value || "standard";
    updateBalanceControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [claimGuardEnabled, claimGuardAfterOutput, claimGuardBanner, claimGuardMode]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.claim_guard_enabled = claimGuardEnabled?.checked !== false;
    stateCache.settings.claim_guard_after_output = claimGuardAfterOutput?.checked !== false;
    stateCache.settings.claim_guard_show_banner = Boolean(claimGuardBanner?.checked);
    stateCache.settings.claim_guard_mode = claimGuardMode?.value || "balanced";
    updateClaimGuardControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [
  adaptiveLearningEnabled,
  adaptiveLearningInject,
  adaptiveLearningDebug,
  adaptiveLearningPerTurn,
  adaptiveLearningExplore,
  adaptiveLearningUserBonus,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.adaptive_learning_enabled = adaptiveLearningEnabled?.checked !== false;
    stateCache.settings.adaptive_learning_inject = adaptiveLearningInject?.checked !== false;
    stateCache.settings.adaptive_learning_debug = Boolean(adaptiveLearningDebug?.checked);
    stateCache.settings.adaptive_learning_per_turn = Number(adaptiveLearningPerTurn?.value || 2);
    stateCache.settings.adaptive_learning_exploration_rate = Number(adaptiveLearningExplore?.value || 0.25);
    stateCache.settings.adaptive_learning_user_bonus = Number(adaptiveLearningUserBonus?.value || 0.2);
    updateAdaptiveLearningControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [
  feedbackEnabled,
  feedbackDebug,
  feedbackSelfLearning,
  feedbackHistoryLimit,
  feedbackWarnB,
  feedbackWarnR,
  feedbackWarnH,
  feedbackSelfPerReport,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.feedback_enabled = feedbackEnabled?.checked !== false;
    stateCache.settings.feedback_debug = Boolean(feedbackDebug?.checked);
    stateCache.settings.feedback_self_learning_enabled = feedbackSelfLearning?.checked !== false;
    stateCache.settings.feedback_history_limit = Number(feedbackHistoryLimit?.value || 25);
    stateCache.settings.feedback_warn_below_b = Number(feedbackWarnB?.value || 0.6);
    stateCache.settings.feedback_warn_below_r = Number(feedbackWarnR?.value || 0.75);
    stateCache.settings.feedback_warn_below_h = Number(feedbackWarnH?.value || 0.65);
    stateCache.settings.feedback_self_learning_per_report = Number(feedbackSelfPerReport?.value || 2);
    updateFeedbackControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
projectSettingsSave?.addEventListener("click", async () => {
  if (!stateCache?.settings) return;
  stateCache.settings.project_memory_enabled = projectMemoryEnabled?.checked !== false;
  stateCache.settings.project_memory_debug = Boolean(projectMemoryDebug?.checked);
  stateCache.settings.project_memory_top_k = Number(projectMemoryTopK?.value || 2);
  stateCache.settings.project_memory_max_chars = Number(projectMemoryMaxChars?.value || 2600);
  updateProjectMemoryControls(stateCache.settings, stateCache);
  await saveSettings(projectSettingsStatus);
});
projectRefresh?.addEventListener("click", () => {
  projectsLoaded = false;
  loadProjectsPanel(true, selectedProjectId());
});
projectNew?.addEventListener("click", newProjectForm);
projectOpen?.addEventListener("click", () => loadProjectsPanel(true, selectedProjectId()));
projectSelect?.addEventListener("change", () => loadProjectsPanel(true, selectedProjectId()));
projectSave?.addEventListener("click", saveProjectFromForm);
projectFormulaAdd?.addEventListener("click", () => addProjectChild("formula"));
projectPaperAdd?.addEventListener("click", () => addProjectChild("paper"));
projectEntryAdd?.addEventListener("click", () => addProjectChild("entry"));
projectSearch?.addEventListener("input", () => {
  const query = projectSearch.value.trim();
  if (!query) {
    if (projectSearchResults) projectSearchResults.innerHTML = "";
    return;
  }
  window.clearTimeout(projectSearch._timer);
  projectSearch._timer = window.setTimeout(() => loadProjectsPanel(true, selectedProjectId(), query), 250);
});
docsSettingsSave?.addEventListener("click", async () => {
  if (!stateCache?.settings) return;
  stateCache.settings.file_builder_enabled = fileBuilderEnabled?.checked !== false;
  stateCache.settings.file_builder_inject_instructions = fileBuilderInject?.checked !== false;
  stateCache.settings.file_builder_replace_blocks = fileBuilderReplace?.checked !== false;
  stateCache.settings.file_builder_show_source_code = fileBuilderSource?.checked !== false;
  stateCache.settings.file_builder_auto_capture_fences = fileBuilderFences?.checked !== false;
  stateCache.settings.file_builder_compile_tex_pdf = fileBuilderCompileTex?.checked !== false;
  stateCache.settings.file_builder_python_syntax_check = fileBuilderPythonCheck?.checked !== false;
  stateCache.settings.file_builder_python_run_enabled = fileBuilderPythonRun?.checked !== false;
  stateCache.settings.file_builder_python_run_in_terminal = fileBuilderTerminal?.checked !== false;
  stateCache.settings.file_builder_inject_feedback = fileBuilderFeedback?.checked !== false;
  stateCache.settings.file_builder_debug = Boolean(fileBuilderDebug?.checked);
  stateCache.settings.file_builder_preview_chars = Number(fileBuilderPreviewChars?.value || 5000);
  updateFileBuilderControls(stateCache.settings, stateCache);
  await saveSettings(docsSettingsStatus);
});
docsRefresh?.addEventListener("click", () => {
  docsLoaded = false;
  loadDocsPanel(true, selectedDocId());
});
docsSelect?.addEventListener("change", () => loadDocsPanel(true, selectedDocId()));
docsOpenFile?.addEventListener("click", openSelectedDoc);
docsOpenPdf?.addEventListener("click", openSelectedPdf);
docsSave?.addEventListener("click", saveManualDoc);
docsRunPython?.addEventListener("click", runSelectedPythonDoc);
docsDelete?.addEventListener("click", deleteSelectedDoc);
for (const control of [emotionEnabled, emotionDebug, emotionMode, emotionLanguage]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.emotion_enabled = emotionEnabled?.checked !== false;
    stateCache.settings.emotion_debug = Boolean(emotionDebug?.checked);
    stateCache.settings.emotion_mode = emotionMode?.value || "full";
    stateCache.settings.emotion_language = emotionLanguage?.value || "auto";
    updateEmotionControls(stateCache.settings);
    await saveSettings();
  });
}
for (const control of [
  offlineWikiEnabled,
  offlineWikiAuto,
  offlineWikiDebug,
  offlineWikiLog,
  offlineWikiPath,
  offlineWikiMaxChars,
  offlineWikiMultiMaxChars,
  offlineWikiMaxTerms,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.offline_wiki_enabled = Boolean(offlineWikiEnabled?.checked);
    stateCache.settings.offline_wiki_auto = offlineWikiAuto?.checked !== false;
    stateCache.settings.offline_wiki_debug = Boolean(offlineWikiDebug?.checked);
    stateCache.settings.offline_wiki_log = offlineWikiLog?.checked !== false;
    stateCache.settings.offline_wiki_zim_path = offlineWikiPath?.value?.trim() || "";
    stateCache.settings.offline_wiki_max_chars = Number(offlineWikiMaxChars?.value || 1400);
    stateCache.settings.offline_wiki_multi_max_chars = Number(offlineWikiMultiMaxChars?.value || 700);
    stateCache.settings.offline_wiki_max_terms = Number(offlineWikiMaxTerms?.value || 2);
    updateOfflineWikiControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [identityEnabled, identityOnce, identityName, identityMode]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.identity_enabled = identityEnabled?.checked !== false;
    stateCache.settings.identity_once = identityOnce?.checked !== false;
    stateCache.settings.identity_name = identityName?.value?.trim() || "MAAT-KI";
    stateCache.settings.identity_mode = identityMode?.value || "balanced";
    updateIdentityControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [engineEnabled, engineShowInChat, engineShowCciDebug, advancedCciEnabled, advancedCciShowDebug, advancedCciKappa]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.engine_enabled = engineEnabled?.checked !== false;
    stateCache.settings.engine_show_in_chat = Boolean(engineShowInChat?.checked);
    stateCache.settings.engine_show_cci_debug = Boolean(engineShowCciDebug?.checked);
    stateCache.settings.advanced_cci_enabled = advancedCciEnabled?.checked !== false;
    stateCache.settings.advanced_cci_show_debug = Boolean(advancedCciShowDebug?.checked);
    stateCache.settings.advanced_cci_kappa = Number(advancedCciKappa?.value || 0.5);
    updateEngineControls(stateCache);
    await saveSettings();
  });
}
for (const control of [reflectionEnabled, reflectionBanner, reflectionPromptRule, reflectionMode]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.reflection_enabled = reflectionEnabled?.checked !== false;
    stateCache.settings.reflection_banner = Boolean(reflectionBanner?.checked);
    stateCache.settings.reflection_prompt_rule = reflectionPromptRule?.checked !== false;
    stateCache.settings.reflection_mode = reflectionMode?.value || "auto";
    updateReflectionControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
for (const control of [
  antihalluEnabled,
  antihalluBanner,
  antihalluGaps,
  antihalluSymbolic,
  antihalluMode,
  antihalluSoftenThreshold,
  antihalluStrictThreshold,
]) {
  control?.addEventListener("change", async () => {
    if (!stateCache?.settings) return;
    stateCache.settings.antihallu_enabled = antihalluEnabled?.checked !== false;
    stateCache.settings.antihallu_show_banner = Boolean(antihalluBanner?.checked);
    stateCache.settings.antihallu_gap_questions = antihalluGaps?.checked !== false;
    stateCache.settings.antihallu_symbolic_lenient = antihalluSymbolic?.checked !== false;
    stateCache.settings.antihallu_mode = antihalluMode?.value || "soften";
    stateCache.settings.antihallu_soften_threshold = Number(antihalluSoftenThreshold?.value || 0.55);
    stateCache.settings.antihallu_strict_threshold = Number(antihalluStrictThreshold?.value || 0.85);
    updateAntiHalluControls(stateCache.settings, stateCache);
    await saveSettings();
  });
}
document.querySelector("#llamaNCtx").addEventListener("input", () => syncCtxInputs("model"));
document.querySelector("#settingsNCtx").addEventListener("input", () => syncCtxInputs("settings"));
document.querySelector("#llamaModelSelect").addEventListener("change", (event) => {
  const path = event.target.value;
  if (path) {
    if (llamaModelPathInput) llamaModelPathInput.value = path;
    syncModelPathInputs("model");
    statusLine.textContent = `GGUF ausgewählt · ${shortPath(path)}`;
  }
});
llamaModelPathInput?.addEventListener("input", () => syncModelPathInputs("model"));
settingsLlamaModelPath?.addEventListener("input", () => syncModelPathInputs("settings"));
applySettingsModelPath?.addEventListener("click", async () => {
  if (!stateCache?.settings) return;
  syncModelPathInputs("settings");
  document.querySelector("#modelAdapter").value = "llama_cpp_direct";
  updateAdapterFields();
  await saveSettings();
  statusLine.textContent = `Manueller Modellpfad gespeichert · ${shortPath(llamaModelPathInput?.value || "")}`;
});
document.querySelector("#refreshGgufModels").addEventListener("click", async () => {
  if (stateCache?.settings && ggufModelDirsCustom) {
    stateCache.settings.gguf_model_dirs_custom = ggufModelDirsCustom.value.trim();
  }
  await saveSettings();
  ggufModelsLoaded = false;
  await loadGgufModels(true);
});
ggufModelDirsCustom?.addEventListener("change", () => {
  if (!stateCache?.settings) return;
  stateCache.settings.gguf_model_dirs_custom = ggufModelDirsCustom.value.trim();
});
chatModelMenuButton.addEventListener("click", async () => {
  await loadGgufModels(false);
  chatFavoriteModel.hidden = !chatFavoriteModel.hidden;
  if (!chatFavoriteModel.hidden) {
    chatFavoriteModel.focus();
  }
});
chatFavoriteModel.addEventListener("change", async (event) => {
  const path = event.target.value;
  if (!path) return;
  chatFavoriteModel.hidden = true;
  document.querySelector("#modelAdapter").value = "llama_cpp_direct";
  if (llamaModelPathInput) llamaModelPathInput.value = path;
  syncModelPathInputs("model");
  updateAdapterFields();
  await saveSettings();
  statusLine.textContent = `Chatmodell gewählt · ${shortPath(path)}`;
});
chatFavoriteModel.addEventListener("blur", () => {
  setTimeout(() => {
    chatFavoriteModel.hidden = true;
  }, 140);
});
chatThinkingToggle.addEventListener("click", async () => {
  if (!stateCache?.settings) return;
  await saveThinkingSetting(!Boolean(stateCache.settings.enable_thinking));
});
sendButton?.addEventListener("click", (event) => {
  if (!isSending) return;
  event.preventDefault();
  event.stopPropagation();
  stopCurrentStream();
});
chatSearch.addEventListener("input", renderChatList);
document.querySelector("#newChat").addEventListener("click", () => {
  activateTab("chat");
  clearChatView();
});
document.querySelector("#historyNewChat").addEventListener("click", () => {
  activateTab("chat");
  clearChatView();
});
document.querySelectorAll("[data-tab]").forEach((tab) => {
  tab.addEventListener("click", () => activateTab(tab.dataset.tab));
});

initThemeScheduler();
loadState().then(() => {
  addMessage("system", "MAAT Web Core bereit. Nutze /help oder stelle eine Frage.");
});
