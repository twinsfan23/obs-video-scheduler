const calendarEl = document.getElementById('calendar');
const timelineEl = document.getElementById('timeline');
const itemPicker = document.getElementById('item-picker');
const loadSelect = document.getElementById('load-file');
const viewButtons = document.querySelectorAll('.view-buttons button');

let calendar;
let scheduleData = [];
let items = [];
let currentSelection = null;

const TZ_OFFSET_MS = new Date().getTimezoneOffset() * 60000;

function toServerScheduleTime(timestampMs) {
  return timestampMs - TZ_OFFSET_MS;
}

function fromServerScheduleTime(timestampMs) {
  return timestampMs + TZ_OFFSET_MS;
}

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (e) {
    return text;
  }
}

function initCalendar() {
  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'timeGridWeek',
    height: 'auto',
    expandRows: true,
    slotDuration: '00:15:00',
    selectable: true,
    editable: true,
    eventResizableFromStart: true,
    headerToolbar: false,
    eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
    select(info) {
      currentSelection = info;
    },
    unselect() {
      currentSelection = null;
    },
    eventDrop(info) {
      reschedule_event(info.event.id, info.event.start.getTime());
    },
    eventResize(info) {
      reschedule_event(info.event.id, info.event.start.getTime());
    },
    eventClick(info) {
      const shouldRemove = confirm(`Remove ${info.event.title}?`);
      if (shouldRemove) {
        remove_event(info.event.id);
      }
    },
  });

  calendar.render();
}

function syncCalendarEvents(schedule) {
  if (!calendar) return;
  calendar.removeAllEvents();
  schedule.forEach((entry) => {
    calendar.addEvent({
      id: entry._id,
      title: entry.name,
      start: new Date(fromServerScheduleTime(entry.start)),
      end: new Date(fromServerScheduleTime(entry.stop)),
      allDay: false,
    });
  });
}

function formatTimeRange(start, stop) {
  const startDate = new Date(start);
  const stopDate = new Date(stop);
  const opts = { hour: '2-digit', minute: '2-digit' };
  return `${startDate.toLocaleTimeString([], opts)} - ${stopDate.toLocaleTimeString([], opts)}`;
}

function renderTimeline(schedule) {
  timelineEl.innerHTML = '';
  if (!schedule.length) {
    timelineEl.textContent = 'No scheduled entries yet. Add items from the calendar or lists.';
    return;
  }

  const adjusted = schedule.map((entry) => ({
    ...entry,
    start: fromServerScheduleTime(entry.start),
    stop: fromServerScheduleTime(entry.stop),
  }));

  const sorted = [...adjusted].sort((a, b) => a.start - b.start);
  const minStart = sorted[0].start;
  const maxStop = Math.max(...sorted.map((s) => s.stop));
  const span = Math.max(maxStop - minStart, 60 * 1000);

  sorted.forEach((entry) => {
    const track = document.createElement('div');
    track.className = 'timeline-track';

    const block = document.createElement('div');
    block.className = 'timeline-block';
    block.style.flexBasis = `${((entry.stop - entry.start) / span) * 100}%`;
    block.style.flexGrow = 0;
    block.dataset.id = entry._id;

    const title = document.createElement('div');
    title.textContent = entry.name;
    const timeRange = document.createElement('div');
    timeRange.className = 'time-range';
    timeRange.textContent = formatTimeRange(entry.start, entry.stop);

    block.appendChild(title);
    block.appendChild(timeRange);

    block.addEventListener('click', () => {
      const suggestion = new Date(entry.start).toISOString().slice(0, 16);
      const nextStart = prompt(`Move ${entry.name} to (local time)`, suggestion);
      if (nextStart) {
        const ts = Date.parse(nextStart);
        if (!Number.isNaN(ts)) {
          reschedule_event(entry._id, ts);
        }
      }
    });

    block.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const shouldRemove = confirm(`Remove ${entry.name}?`);
      if (shouldRemove) {
        remove_event(entry._id);
      }
    });

    track.appendChild(block);
    timelineEl.appendChild(track);
  });
}

async function update_schedule() {
  try {
    const data = await jsonFetch('/ScheduleGet');
    if (typeof data === 'string' && data === 'no-op') {
      return;
    }
    scheduleData = data.schedule || [];
    syncCalendarEvents(scheduleData);
    renderTimeline(scheduleData);
  } catch (err) {
    console.error('Schedule update failed', err);
  }
}

async function update_status(endpoint, targetId) {
  try {
    const text = await jsonFetch(endpoint);
    document.getElementById(targetId).innerHTML = typeof text === 'string' ? text : JSON.stringify(text);
  } catch (err) {
    console.error('Status update failed', err);
  }
}

async function update_video_list() {
  try {
    const html = await jsonFetch('/VideoList?type=video');
    document.getElementById('videoList').innerHTML = html;
  } catch (err) {
    console.error('Video list update failed', err);
  }
}

async function update_activity_list() {
  try {
    const html = await jsonFetch('/VideoList?type=activity');
    document.getElementById('activityList').innerHTML = html;
  } catch (err) {
    console.error('Activity list update failed', err);
  }
}

async function refreshItemsForPicker() {
  try {
    const videos = await jsonFetch('/VideoList?type=video&format=json');
    const activities = await jsonFetch('/VideoList?type=activity&format=json');
    items = [...(videos || []), ...(activities || [])];

    itemPicker.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.textContent = 'Select an item to schedule';
    placeholder.value = '';
    itemPicker.appendChild(placeholder);

    items.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.uuid;
      option.textContent = `${item.name} (${Math.round(item.duration / 60000)} min)`;
      option.dataset.duration = item.duration;
      itemPicker.appendChild(option);
    });
  } catch (err) {
    console.error('Picker update failed', err);
  }
}

async function refreshLoadOptions() {
  try {
    const files = await jsonFetch('/ScheduleList?format=json');
    loadSelect.innerHTML = '';
    (files || []).forEach((file) => {
      const option = document.createElement('option');
      option.value = file;
      option.textContent = file;
      loadSelect.appendChild(option);
    });
  } catch (err) {
    console.error('Load list update failed', err);
  }
}

async function startContest() {
  await fetch('/StartContest');
}

async function rescheduleContest() {
  const time = document.getElementById('reschedule-time').value;
  await fetch(`/StartContest?time=${encodeURIComponent(time)}`);
}

async function saveSchedule() {
  const file = document.getElementById('save-file-name').value;
  await fetch(`/SaveSchedule?file=${encodeURIComponent(file)}`);
  refreshLoadOptions();
}

async function loadSchedule() {
  const file = loadSelect.value;
  await fetch(`/LoadSchedule?file=${encodeURIComponent(file)}`);
  update_schedule();
}

async function add_event(uuid, start) {
  const payloadStart = typeof start === 'number' ? toServerScheduleTime(start) : undefined;
  const payload = payloadStart !== undefined ? { uuid, start: payloadStart } : { uuid };
  const result = await jsonFetch('/api/schedule/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (result.schedule) {
    scheduleData = result.schedule;
    syncCalendarEvents(scheduleData);
    renderTimeline(scheduleData);
  }
}

async function remove_event(uuid) {
  const result = await jsonFetch('/api/schedule/remove', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uuid }),
  });
  if (result.schedule) {
    scheduleData = result.schedule;
    syncCalendarEvents(scheduleData);
    renderTimeline(scheduleData);
  }
}

async function reschedule_event(uuid, new_start) {
  const adjustedStart = toServerScheduleTime(new_start);
  const result = await jsonFetch('/api/schedule/reschedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uuid, start: adjustedStart }),
  });
  if (result.schedule) {
    scheduleData = result.schedule;
    syncCalendarEvents(scheduleData);
    renderTimeline(scheduleData);
  }
}

async function add_activity() {
  const name = document.getElementById('activity-name').value;
  const duration = document.getElementById('activity-duration').value;
  await fetch(`/AddActivity?name=${encodeURIComponent(name)}&duration=${encodeURIComponent(duration)}`);
  update_activity_list();
  refreshItemsForPicker();
}

function scheduleFromSelection() {
  const uuid = itemPicker.value;
  if (!uuid) {
    alert('Pick a video or activity first.');
    return;
  }

  const selectedItem = items.find((i) => i.uuid === uuid);
  const duration = selectedItem ? selectedItem.duration : 0;

  if (!currentSelection) {
    add_event(uuid);
    return;
  }

  const start = currentSelection.start.getTime();
  const calculatedStart = start;
  const calculatedStop = duration ? start + duration : currentSelection.end.getTime();

  add_event(uuid, calculatedStart).then(() => {
    if (duration && calendar) {
      // place the new event visually by refreshing schedule
      update_schedule();
    }
  });

  currentSelection = null;
  if (calendar) {
    calendar.unselect();
  }
}

function wireControls() {
  document.getElementById('start-button').addEventListener('click', startContest);
  document.getElementById('reschedule-button').addEventListener('click', rescheduleContest);
  document.getElementById('save-button').addEventListener('click', saveSchedule);
  document.getElementById('load-button').addEventListener('click', loadSchedule);
  document.getElementById('schedule-selection').addEventListener('click', scheduleFromSelection);

  viewButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (calendar) {
        calendar.changeView(btn.dataset.view);
      }
    });
  });
}

function bootstrap() {
  initCalendar();
  wireControls();

  update_schedule();
  update_status('/CurrentState', 'current-state');
  update_status('/ContestState', 'contest-state');
  update_status('/OBSStatus.jsp', 'obs-status');
  update_video_list();
  update_activity_list();
  refreshItemsForPicker();
  refreshLoadOptions();

  setInterval(() => update_status('/ContestState', 'contest-state'), 3000);
  setInterval(() => update_status('/OBSStatus.jsp', 'obs-status'), 3000);
  setInterval(() => update_status('/CurrentState', 'current-state'), 3000);
  setInterval(update_schedule, 5000);
}

bootstrap();

// Expose hooks used by server-rendered lists
window.add_event = add_event;
window.remove_event = remove_event;
window.reschedule_event = reschedule_event;
window.add_activity = add_activity;
window.start = startContest;
window.reschedule = rescheduleContest;
window.save = saveSchedule;
window.load = loadSchedule;
