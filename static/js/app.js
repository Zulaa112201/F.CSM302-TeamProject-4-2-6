
"use strict";

const $ = (id) => document.getElementById(id);

const elements = {
    numbers: $("numbers"),
    datasetSize: $("datasetSize"),
    datasetSizeValue: $("datasetSizeValue"),
    leftCount: $("leftCount"),
    rightCount: $("rightCount"),
    leftPreview: $("leftPreview"),
    rightPreview: $("rightPreview"),
    leftWorkerBars: $("leftWorkerBars"),
    rightWorkerBars: $("rightWorkerBars"),
    sampleButton: $("sampleButton"),
    startButton: $("startButton"),
    pauseButton: $("pauseButton"),
    resumeButton: $("resumeButton"),
    resetButton: $("resetButton"),
    playbackSpeed: $("playbackSpeed"),
    algorithm: $("algorithm"),
    stepInfo: $("stepInfo"),
    progressFill: $("progressFill"),
    error: $("error"),
    bars: $("bars"),
    sortedBars: $("sortedBars"),
    sortedMeta: $("sortedMeta"),
    sortedPreview: $("sortedPreview"),
    arrayMeta: $("arrayMeta"),
    seqTime: $("seqTime"),
    seqResult: $("seqResult"),
    parTime: $("parTime"),
    parResult: $("parResult"),
    comparison: $("comparison"),
    threadSummary: $("threadSummary"),
    threadLegend: $("threadLegend"),
    threadLog: $("threadLog"),
    timeline: $("timeline"),
    benchmarkButton: $("benchmarkButton"),
    benchmarkStatus: $("benchmarkStatus"),
    performanceChart: $("performanceChart"),
    benchmarkLegend: $("benchmarkLegend")
};

let originalNumbers = [];
let sortedNumbers = [];
let events = [];
let currentEventIndex = 0;
let animationTimer = null;
let isPaused = false;
let isRunning = false;
let lastBenchmark = null;

const threadColors = [
    "#718dff",
    "#56e0bd",
    "#b09aff",
    "#ffb66e",
    "#ff82a8"
];

function showError(message) {
    elements.error.textContent = message;
    elements.error.hidden = false;
}

function clearError() {
    elements.error.textContent = "";
    elements.error.hidden = true;
}

function setProgress(percent) {
    elements.progressFill.style.width =
        `${Math.max(0, Math.min(100, percent))}%`;
}

function formatMilliseconds(value) {
    if (
        value === undefined ||
        value === null ||
        !Number.isFinite(Number(value))
    ) {
        return "—";
    }

    return `${Number(value).toFixed(3)} ms`;
}

function parseInput() {
    const raw = elements.numbers.value.trim();

    if (!raw) {
        throw new Error("Тоон утга оруулна уу.");
    }

    // Зөвхөн таслалаар тусгаарлана.
    // Эхэндээ болон хамгийн сүүлд таслал тавихыг хориглоно.
    if (raw.startsWith(",") || raw.endsWith(",")) {
        throw new Error(
            "Эхэнд болон хамгийн сүүлд таслал тавьж болохгүй."
        );
    }

    const parts = raw.split(",");

    if (parts.some(part => part.trim() === "")) {
        throw new Error(
            "Тоонуудын хооронд таслал тавьж, хоосон утга үлдээхгүй байна уу."
        );
    }

    const values = parts.map(part => part.trim());

    if (values.length < 4) {
        throw new Error(
            "Эрэмбэлэхийн тулд 4 болон түүнээс дээш тоо оруулна уу."
        );
    }

    const limits = window.SORT_LIMITS || {};
    const algorithm = elements.algorithm?.value;
    const limit = limits[algorithm] || 5000;

    if (values.length > limit) {
        throw new Error(`Хамгийн ихдээ ${limit} тоо оруулна уу.`);
    }

    return values.map(part => {
        if (!/^-?\d+$/.test(part)) {
            throw new Error(`Буруу бүхэл тоо байна: ${part}`);
        }

        const number = Number(part);

        if (!Number.isSafeInteger(number)) {
            throw new Error(`Тоон утга хэт том байна: ${part}`);
        }

        return number;
    });
}

function updateSplitPreview(values) {
    const middle = Math.ceil(values.length / 2);
    const left = values.slice(0, middle);
    const right = values.slice(middle);

    if (elements.leftCount) {
        elements.leftCount.textContent = `${left.length} утга`;
    }

    if (elements.rightCount) {
        elements.rightCount.textContent = `${right.length} утга`;
    }

    if (elements.leftPreview) {
        elements.leftPreview.textContent =
            left.length ? left.join(", ") : "—";
    }

    if (elements.rightPreview) {
        elements.rightPreview.textContent =
            right.length ? right.join(", ") : "—";
    }

    renderWorkerBars(elements.leftWorkerBars, left, "left");
    renderWorkerBars(elements.rightWorkerBars, right, "right");
}

function renderWorkerBars(container, values, side) {
    if (!container) return;

    container.replaceChildren();

    if (!values.length) return;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    values.forEach((value, index) => {
        const item = document.createElement("div");
        item.className = "worker-bar-item";

        const bar = document.createElement("div");
        bar.className =
            `worker-bar ${side === "left" ? "worker-bar-left" : "worker-bar-right"}`;

        bar.style.height =
            `${Math.max(8, 12 + ((value - min) / range) * 62)}px`;

        bar.title =
            `Worker ${side === "left" ? 0 : 1} · индекс ${index} · утга ${value}`;

        const label = document.createElement("span");
        label.textContent = String(value);

        item.append(bar, label);
        container.appendChild(item);
    });
}


function renderSortedBars(values, event = null) {
    const container = elements.sortedBars;
    if (!container) return;

    container.replaceChildren();

    const nums = Array.isArray(values) ? values : [];

    if (elements.sortedMeta) {
        elements.sortedMeta.textContent =
            nums.length ? `${nums.length} тоо` : "Эцсийн үр дүн";
    }

    if (elements.sortedPreview) {
        elements.sortedPreview.textContent = nums.length
            ? nums.join(", ")
            : "Эрэмбэлсний дараах үр дүн энд харагдана.";
    }

    if (!nums.length) return;

    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const range = max - min || 1;

    // Алхам бүрийн task болон kind-аас шалтгаалж динамикаар өнгө ялгах
    const taskText = event?.task || "";
    const isSwapping = taskText.includes("соль") || taskText.includes("байрлал") || event?.kind === "merge";

    nums.forEach((value, index) => {
        const item = document.createElement("div");
        item.className = "bar-item";

        const bar = document.createElement("div");
        bar.className = "bar";

        bar.style.height =
            `${max === min ? 65 : 12 + ((value - min) / range) * 88}%`;

        // Анхдагч өнгө (Цэнхэр)
        bar.style.background = "linear-gradient(180deg, #6489D8, #4266B5)";

        // Хэрэв эрэмбэлэгдэж дууссан бол ногоон болгох
        if (event?.kind === "finish") {
            bar.style.background = "linear-gradient(180deg, #36D399, #15966A)";
        } 
        // Явцын дунд хийгдэж буй үйлдэл дээр шар/улбар шар эсвэл улаан өнгө өгөх
        else if (isSwapping) {
            bar.style.background = "linear-gradient(180deg, #FF7777, #D93636)"; // Улаан (Солилцох үед)
        } else {
            bar.style.background = "linear-gradient(180deg, #FFD166, #E5A03D)"; // Шар (Харьцуулах/хайх үед)
        }

        bar.title = `Индекс: ${index}, утга: ${value}`;

        const label = document.createElement("span");
        label.className = "bar-label";
        label.textContent = String(value);

        item.append(bar, label);
        container.appendChild(item);
    });
}

function renderBars(values, sortedSet = null) {
    elements.bars.replaceChildren();

    if (!values.length) {
        elements.arrayMeta.textContent = "0 ITEMS";
        updateSplitPreview([]);
        return;
    }

    updateSplitPreview(values);

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    elements.arrayMeta.textContent = `${values.length} ITEMS`;

    values.forEach((value, index) => {
        const item = document.createElement("div");
        item.className = "bar-item";

        const bar = document.createElement("div");
        bar.className = "bar";

        const height = max === min
            ? 65
            : 12 + ((value - min) / range) * 88;

        bar.style.height = `${height}%`;
        bar.title = `Индекс: ${index}, утга: ${value}`;

        if (sortedSet && sortedSet.has(index)) {
            bar.style.background =
                "linear-gradient(180deg, #73efd4, #2bbda4)";
        }

        const label = document.createElement("span");
        label.className = "bar-label";
        label.textContent = String(value);

        item.append(bar, label);
        elements.bars.appendChild(item);
    });
}

function resetResults() {
    elements.seqTime.textContent = "—";
    elements.parTime.textContent = "—";

    elements.seqResult.textContent = "Үр дүн хүлээгдэж байна.";
    elements.parResult.textContent = "Үр дүн хүлээгдэж байна.";

    elements.comparison.textContent =
        "Хоёр алгоритмын үр дүнг энд харуулна.";
}

function stopAnimation() {
    if (animationTimer !== null) {
        clearTimeout(animationTimer);
        animationTimer = null;
    }

    isRunning = false;
}

function resetAnimation() {
    stopAnimation();
    isPaused = false;
    currentEventIndex = 0;

    elements.threadLog.replaceChildren();
    elements.threadLegend.replaceChildren();
    elements.timeline.replaceChildren();

    elements.stepInfo.textContent = events.length
        ? "Тоглуулах товчийг дарж алхмуудыг ажиглана уу."
        : "Эхлээд эрэмбэлэлтийг ажиллуулна уу.";

    setProgress(0);
    renderBars(originalNumbers);
    renderSortedBars([]);

    elements.threadSummary.textContent =
        "Тоглуулж эхлэхэд thread-ийн event-үүд энд харагдана.";

    elements.timeline.textContent =
        "Тоглуулах товчийг дарж timeline-ийг алхам алхмаар үүсгэнэ үү.";

    elements.startButton.disabled = events.length === 0;
    elements.pauseButton.disabled = true;
    elements.resumeButton.disabled = true;
    elements.resetButton.disabled = events.length === 0;
}

function getThreadColor(threadName, threadNames) {
    const index = threadNames.indexOf(threadName);
    return threadColors[Math.max(0, index) % threadColors.length];
}

function renderThreadLegend(threadNames) {
    elements.threadLegend.replaceChildren();

    threadNames.forEach((name, index) => {
        const item = document.createElement("span");
        item.className = "legend-item";

        const swatch = document.createElement("i");
        swatch.className = "legend-swatch";
        swatch.style.background =
            threadColors[index % threadColors.length];

        const label = document.createElement("span");
        label.textContent = name;

        item.append(swatch, label);
        elements.threadLegend.appendChild(item);
    });
}

function renderThreadSummary() {
    const threadNames = [
        ...new Set(events.map((event) => event.thread || "Unknown"))
    ];

    elements.threadSummary.textContent =
        `${threadNames.length} thread · ${events.length} recorded events`;

    renderThreadLegend(threadNames);
    renderTimeline(events, threadNames);
}

function renderTimeline(allEvents, threadNames) {
    const timeline = elements.timeline;
    timeline.replaceChildren();

    if (!Array.isArray(allEvents) || allEvents.length === 0) {
        timeline.textContent = "Thread-ийн үйл явдал хараахан алга.";
        return;
    }

    const names = threadNames?.length
        ? threadNames
        : [...new Set(allEvents.map((event) => event.thread || "Unknown"))];

    const maxTime = Math.max(
        1,
        ...allEvents.map((event) => Number(event.at) || 0)
    );

    const axis = document.createElement("div");
    axis.className = "timeline-axis";
    axis.innerHTML = `
        <span>0 ms</span>
        <span>${(maxTime / 2).toFixed(2)} ms</span>
        <span>${maxTime.toFixed(2)} ms</span>
    `;

    timeline.appendChild(axis);

    names.forEach((threadName, index) => {
        const threadEvents = allEvents
            .filter((event) => (event.thread || "Unknown") === threadName)
            .slice()
            .sort((a, b) => Number(a.at || 0) - Number(b.at || 0));

        const row = document.createElement("div");
        row.className = "timeline-row";

        const label = document.createElement("div");
        label.className = "timeline-name";
        label.textContent = threadName;

        const track = document.createElement("div");
        track.className = "timeline-track";

        let startTime = null;
        let hasActivity = false;

        threadEvents.forEach((event) => {
            const time = Math.max(0, Number(event.at) || 0);

            if (event.kind === "start") {
                startTime = time;
                return;
            }

            if (event.kind === "finish" && startTime !== null) {
                const endTime = Math.max(time, startTime + 0.05);

                addSegment(startTime, endTime, event.task || threadName);
                startTime = null;
                hasActivity = true;
                return;
            }

            if (event.kind === "step" || event.kind === "merge") {
                const marker = document.createElement("div");
                marker.className =
                    "timeline-segment timeline-marker";

                marker.style.left =
                    `${Math.min(99.5, time / maxTime * 100)}%`;

                marker.style.width = "5px";
                marker.style.background =
                    threadColors[index % threadColors.length];

                marker.title =
                    `${time.toFixed(3)} ms — ${event.task || event.kind}`;

                track.appendChild(marker);
                hasActivity = true;
            }
        });

        if (startTime !== null) {
            addSegment(startTime, maxTime, "Ажиллаж байна");
            hasActivity = true;
        }

        if (!hasActivity && threadEvents.length) {
            const firstTime = Math.max(
                0,
                Number(threadEvents[0].at) || 0
            );

            addSegment(firstTime, maxTime, threadName);
        }

        function addSegment(start, end, description) {
            const segment = document.createElement("div");
            segment.className = "timeline-segment";

            const left = Math.min(99, start / maxTime * 100);
            const width = Math.max(
                0.8,
                Math.min(100 - left, (end - start) / maxTime * 100)
            );

            segment.style.left = `${left}%`;
            segment.style.width = `${width}%`;
            segment.style.background =
                threadColors[index % threadColors.length];

            segment.title =
                `${threadName}: ${start.toFixed(3)}–${end.toFixed(3)} ms · ${description}`;

            track.appendChild(segment);
        }

        row.append(label, track);
        timeline.appendChild(row);
    });
}

function describeEvent(event) {
    const task = event.task || "Sorting task";

    if (event.kind === "start") {
        return `▶ ${task} эхэллээ`;
    }

    if (event.kind === "finish") {
        return `✓ ${task} дууслаа`;
    }

    if (event.kind === "merge") {
        return `⇄ ${task}`;
    }

    if (event.kind === "step") {
        return `↔ ${task}`;
    }

    return `${event.kind || "event"}: ${task}`;
}

function addThreadLogEntry(event) {
    const threadNames = [
        ...new Set(events.map((item) => item.thread || "Unknown"))
    ];

    const threadName = event.thread || "Unknown";
    const li = document.createElement("li");

    const swatch = document.createElement("i");
    swatch.className = "legend-swatch";
    swatch.style.background =
        getThreadColor(threadName, threadNames);

    const text = document.createElement("span");
    text.textContent =
        `[${Number(event.at || 0).toFixed(2)} ms] ${threadName}: ${describeEvent(event)}`;

    li.append(swatch, text);
    elements.threadLog.prepend(li);

    while (elements.threadLog.children.length > 30) {
        elements.threadLog.lastElementChild.remove();
    }
}

function applyEvent(event) {
    addThreadLogEntry(event);

    const playedEvents = events.slice(0, currentEventIndex);
    const threadNames = [
        ...new Set(playedEvents.map((item) => item.thread || "Unknown"))
    ];

    elements.threadSummary.textContent =
        `${threadNames.length} thread · ${playedEvents.length} / ${events.length} event`;

    renderThreadLegend(threadNames);
    renderTimeline(playedEvents, threadNames);

    if (Array.isArray(event.values)) {
        updateSplitPreview(event.values);

        // Харьцуулж болон сольж байгаа элементүүдийг тодруулна.
        renderSortedBars(event.values, event);
    }

    const percent = events.length
        ? (currentEventIndex / events.length) * 100
        : 0;

    setProgress(percent);

    elements.stepInfo.textContent =
        `Алхам ${currentEventIndex} / ${events.length}: ${describeEvent(event)}`;
}

function playNextEvent() {
    if (isPaused || !isRunning) return;

    if (currentEventIndex >= events.length) {
        stopAnimation();
        setProgress(100);

        elements.stepInfo.textContent =
            "✓ Animation дууслаа · Бүх утга эрэмбэлэгдсэн.";

        // Анхны өгөгдлийг хэвээр үлдээнэ; үр дүнг гурав дахь графикт харуулна.
        renderBars(originalNumbers);
        renderSortedBars(sortedNumbers);

        elements.startButton.disabled = false;
        elements.pauseButton.disabled = true;
        elements.resumeButton.disabled = true;
        return;
    }

    const event = events[currentEventIndex];
    currentEventIndex += 1;

    applyEvent(event);

    const delay = Number(elements.playbackSpeed?.value || 60);
    animationTimer = setTimeout(playNextEvent, delay);
}

function startAnimation() {
    if (!events.length) {
        runSort({ autoPlay: true });
        return;
    }

    if (isRunning) return;

    if (currentEventIndex >= events.length) {
        resetAnimation();
    }

    isRunning = true;
    isPaused = false;

    elements.startButton.disabled = true;
    elements.pauseButton.disabled = false;
    elements.resumeButton.disabled = true;
    elements.resetButton.disabled = false;

    playNextEvent();
}

function pauseAnimation() {
    if (!isRunning) return;

    isPaused = true;
    stopAnimation();

    elements.pauseButton.disabled = true;
    elements.resumeButton.disabled = false;
    elements.stepInfo.textContent = "Animation түр зогссон.";
}

function resumeAnimation() {
    if (!isPaused) return;

    isPaused = false;
    isRunning = true;

    elements.pauseButton.disabled = false;
    elements.resumeButton.disabled = true;

    playNextEvent();
}

async function runSort(options = {}) {
    const autoPlay = options.autoPlay === true;

    clearError();
    stopAnimation();

    elements.stepInfo.textContent = "Эрэмбэлэлт эхэлж байна...";
    setProgress(0);

    try {
        originalNumbers = parseInput();
        sortedNumbers = [];
        events = [];
        currentEventIndex = 0;
        isPaused = false;

        const selectedAlgorithm = elements.algorithm?.value || "merge_sort";

        renderBars(originalNumbers);
    renderSortedBars([]);
        resetResults();

        elements.threadLog.replaceChildren();
        elements.threadLegend.replaceChildren();
        elements.timeline.replaceChildren();

        elements.startButton.disabled = true;
        elements.pauseButton.disabled = true;
        elements.resumeButton.disabled = true;
        elements.resetButton.disabled = true;

        const response = await fetch("/api/sort/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/x-ndjson"
            },
            body: JSON.stringify({
                numbers: originalNumbers,
                algorithm: selectedAlgorithm
            })
        });

        if (!response.ok) {
            const text = await response.text();
            let message = "Эрэмбэлэх хүсэлт амжилтгүй.";

            try {
                message = JSON.parse(text).error || message;
            } catch {}

            throw new Error(message);
        }

        if (!response.body) {
            throw new Error(
                "Серверийн streaming хариу дэмжигдэхгүй байна."
            );
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = "";
        let resultReceived = false;

        async function handleLine(line) {
            if (!line.trim()) return;

            let message;

            try {
                message = JSON.parse(line);
            } catch {
                throw new Error(
                    "Серверээс буцсан event-ийн формат буруу."
                );
            }

            if (message.type === "error") {
                throw new Error(
                    message.error || "Эрэмбэлэлтэд алдаа гарлаа."
                );
            }

            if (message.type === "event") {
                events.push(message.event);

                elements.stepInfo.textContent =
                    `${events.length} event бэлэн · Тоглуулах товчийг дарна уу.`;
            }

            if (message.type === "result") {
                const data = message.data;
                resultReceived = true;

                const algorithmName =
                    data.algorithm_name ||
                    elements.algorithm?.selectedOptions?.[0]?.text ||
                    selectedAlgorithm;

                // Сонгосон алгоритмын эрэмбэлсэн үр дүн.
                sortedNumbers = data.sequential_result || [];
                renderSortedBars(sortedNumbers);

                const resultLabels =
                    document.querySelectorAll(".result-label");

                if (resultLabels[0]) {
                    resultLabels[0].textContent =
                        `SEQUENTIAL ${algorithmName.toUpperCase()}`;
                }

                if (resultLabels[1]) {
                    resultLabels[1].textContent =
                        "PARALLEL MERGE SORT";
                }

                // Flask API хугацааг миллисекундээр буцаадаг.
                elements.seqTime.textContent =
                    formatMilliseconds(data.sequential_ms);

                elements.parTime.textContent =
                    formatMilliseconds(data.parallel_ms);

                elements.seqResult.textContent =
                    sortedNumbers.join(", ");

                elements.parResult.textContent =
                    (data.parallel_result || []).join(", ");

                elements.comparison.textContent = data.same_result
                    ? `✓ ${algorithmName} болон Parallel Merge Sort-ийн үр дүн ижил байна.`
                    : "⚠ Алгоритмуудын үр дүн зөрүүтэй байна.";

                // Олон алхамтай алгоритмын алхмуудыг санах ойд багтаахын тулд
                // сервер зарим алхмыг алгасаж бичдэг. Үүнийг хэрэглэгчид мэдэгдэнэ.
                if (data.stride > 1) {
                    elements.comparison.textContent +=
                        ` Нийт ${data.total_steps} алхмын ` +
                        `${data.shown_events}-г харуулж байна ` +
                        `(${data.stride} алхам тутамд нэг).`;
                }
            }
        }

        while (true) {
            const { value, done } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                await handleLine(line);
            }
        }

        buffer += decoder.decode();

        if (buffer.trim()) {
            await handleLine(buffer);
        }

        if (!resultReceived) {
            throw new Error(
                "Сервер эрэмбэлэлтийн эцсийн үр дүнг буцаасангүй."
            );
        }

        renderBars(originalNumbers);
    renderSortedBars([]);

        elements.threadSummary.textContent =
            `${events.length} event бэлэн · Тоглуулах товчийг дарж ажиглана уу.`;

        elements.timeline.replaceChildren();
        elements.timeline.textContent =
            "Тоглуулах товчийг дарахад thread бүрийн timeline алхам алхмаар гарна.";

        elements.threadLog.replaceChildren();
        elements.threadLegend.replaceChildren();

        setProgress(0);
        currentEventIndex = 0;

        elements.stepInfo.textContent =
            `Бэлэн · ${events.length} event · Алхамчилсан тоглуулалт`;

        elements.startButton.disabled = events.length === 0;
        elements.pauseButton.disabled = true;
        elements.resumeButton.disabled = true;
        elements.resetButton.disabled = events.length === 0;

        if (autoPlay && events.length > 0) {
            startAnimation();
        }

    } catch (error) {
        showError(error.message || "Алдаа гарлаа.");
        elements.stepInfo.textContent = "Эрэмбэлэлт амжилтгүй.";

        elements.startButton.disabled = false;
        elements.pauseButton.disabled = true;
        elements.resumeButton.disabled = true;
        elements.resetButton.disabled = events.length === 0;
    }
}

function generateRandomNumbers() {
    const count = Number(elements.datasetSize?.value || 12);

    const values = Array.from(
        { length: count },
        () => Math.floor(Math.random() * 99) + 1
    );

    elements.numbers.value = values.join(", ");

    if (elements.datasetSizeValue) {
        elements.datasetSizeValue.textContent = String(count);
    }

    clearError();
    resetResults();
    renderBars(values);
}

function drawBenchmarkChart(results) {
    const canvas = elements.performanceChart;
    if (!canvas) return;

    const context = canvas.getContext("2d");

    if (!context) {
        if (elements.benchmarkStatus) {
            elements.benchmarkStatus.textContent =
                "Canvas график ажиллахгүй байна.";
        }
        return;
    }

    const rows = Array.isArray(results) ? results : [];

    const rect = canvas.getBoundingClientRect();
    const width = Math.max(320, Math.floor(rect.width || 640));
    const height = Math.max(260, Math.floor(rect.height || 320));
    const ratio = window.devicePixelRatio || 1;

    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);

    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    context.font = "12px Segoe UI";
    context.textAlign = "left";
    context.textBaseline = "alphabetic";

    if (!rows.length || !rows[0].algorithm_ms) {
        context.fillStyle = "#9aa8c8";
        context.fillText(
            "Benchmark ажиллуулж график үүсгэнэ үү.",
            16,
            28
        );
        return;
    }

    const row = rows[rows.length - 1];
    const names = Object.keys(row.algorithm_ms);

    const colors = [
        "#8297ff",
        "#ff9bca",
        "#56e0bd",
        "#ffbd69",
        "#b69aff",
        "#62c8ff",
        "#f47768",
        "#c2d66b"
    ];

    const values = names.map((name) => ({
        name,
        time: row.algorithm_ms[name]
    }));

    const validValues = values
        .filter((item) =>
            item.time !== null &&
            item.time !== undefined &&
            Number.isFinite(Number(item.time))
        )
        .map((item) => Number(item.time));

    if (!validValues.length) {
        context.fillStyle = "#9aa8c8";
        context.fillText(
            "Харуулах benchmark үр дүн алга.",
            16,
            28
        );
        return;
    }

    const maxValue = Math.max(0.001, ...validValues) * 1.2;

    const chartLeft = Math.min(170, width * 0.36);
    const chartRight = width - 65;
    const chartTop = 30;
    const chartBottom = height - 35;
    const chartWidth = Math.max(1, chartRight - chartLeft);
    const chartHeight = Math.max(1, chartBottom - chartTop);

    const rowHeight = chartHeight / Math.max(values.length, 1);
    const barHeight = Math.min(22, rowHeight * 0.62);

    // Гарчиг
    context.fillStyle = "#e2e8ff";
    context.font = "bold 13px Segoe UI";
    context.fillText(
        `Algorithm performance — ${row.size} items`,
        12,
        17
    );

    // Хэвтээ тор болон хугацааны хуваарь
    context.font = "10px Consolas, monospace";
    context.textAlign = "center";

    for (let i = 0; i <= 4; i++) {
        const x = chartLeft + (chartWidth * i) / 4;
        const value = (maxValue * i) / 4;

        context.strokeStyle = "rgba(160,180,225,0.18)";
        context.beginPath();
        context.moveTo(x, chartTop);
        context.lineTo(x, chartBottom);
        context.stroke();

        context.fillStyle = "#9aa8c8";
        context.fillText(
            `${value.toFixed(2)} ms`,
            x,
            height - 12
        );
    }

    // Алгоритм бүрийн багана
    values.forEach((item, index) => {
        const y = chartTop + rowHeight * index + rowHeight / 2;

        context.textAlign = "right";
        context.font = "11px Segoe UI";
        context.fillStyle = "#c4cee8";
        context.fillText(
            item.name,
            chartLeft - 10,
            y + 4
        );

        if (
            item.time === null ||
            item.time === undefined ||
            !Number.isFinite(Number(item.time))
        ) {
            context.textAlign = "left";
            context.fillStyle = "#9aa8c8";
            context.fillText(
                "Алгассан (>1000 эсвэл дэмжигдээгүй)",
                chartLeft + 5,
                y + 4
            );
            return;
        }

        const time = Number(item.time);
        const barWidth = (time / maxValue) * chartWidth;

        context.fillStyle = colors[index % colors.length];
        context.fillRect(
            chartLeft,
            y - barHeight / 2,
            Math.max(1, barWidth),
            barHeight
        );

        context.textAlign = "left";
        context.fillStyle = "#e2e8ff";
        context.font = "10px Consolas, monospace";
        context.fillText(
            `${time.toFixed(3)} ms`,
            Math.min(chartLeft + barWidth + 6, width - 55),
            y + 4
        );
    });

    if (elements.benchmarkStatus) {
        elements.benchmarkStatus.textContent =
            `Benchmark дууслаа. ${row.size} тоо, ` +
            `${validValues.length}/${names.length} алгоритм хэмжигдсэн.`;
    }
}


function renderBenchmarkLegend() {
    const colors = ["#8297ff", "#ff9bca", "#56e0bd", "#ffbd69", "#b69aff", "#62c8ff", "#f47768", "#c2d66b"];
    const names = lastBenchmark?.[0]?.algorithm_ms ? Object.keys(lastBenchmark[0].algorithm_ms) : ["Sequential", "Parallel"];
    elements.benchmarkLegend.innerHTML = names.map((name, index) =>
        `<span><i style="background:${colors[index % colors.length]}"></i> ${name}</span>`
    ).join("");
}


async function runBenchmark() {
    const button = elements.benchmarkButton;

    try {
        const raw = elements.numbers.value.trim();

        const parts = raw.split(/[\s,;]+/).filter(Boolean);
        const numbers = parts.map(Number);

        if (numbers.length < 4 || numbers.length > 5000) {
            throw new Error("4–5000 бүхэл тоо оруулна уу.");
        }

        if (numbers.some((n) => !Number.isSafeInteger(n))) {
            throw new Error("Зөвхөн бүхэл тоо оруулна уу.");
        }

        if (button) button.disabled = true;

        console.log("Benchmark input:", numbers);

        const response = await fetch("/api/benchmark", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ numbers })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Benchmark хүсэлт амжилтгүй.");
        }

        lastBenchmark = data.results || [];

        console.log("Benchmark response:", lastBenchmark);

        drawBenchmarkChart(lastBenchmark);
        renderBenchmarkLegend();

    } catch (error) {
        console.error("Benchmark error:", error);
        alert(error.message);
    } finally {
        if (button) button.disabled = false;
    }
}

elements.numbers.addEventListener("input", () => {
    const raw = elements.numbers.value.trim();

    if (!raw) {
        showError("Тоон утга оруулна уу.");

        originalNumbers = [];
        sortedNumbers = [];
        events = [];
        currentEventIndex = 0;

        stopAnimation();
        renderBars([]);
        renderSortedBars([]);
        resetResults();
        setProgress(0);

        elements.stepInfo.textContent =
            "Тоон утга оруулсны дараа эрэмбэлнэ үү.";

        elements.startButton.disabled = true;
        elements.pauseButton.disabled = true;
        elements.resumeButton.disabled = true;
        elements.resetButton.disabled = true;

        return;
    }

    try {
        const values = parseInput();

        clearError();
        originalNumbers = values;

        renderBars(values);
        renderSortedBars([]);
        resetResults();

        elements.stepInfo.textContent =
            `${values.length} тоо · Эрэмбэлэхэд бэлэн.`;

        elements.startButton.disabled = false;
    } catch (error) {
        showError(error.message);

        // Буруу өгөгдлөөр эрэмбэлэлт эхлүүлэхгүй.
        elements.startButton.disabled = true;
    }
});

elements.datasetSize?.addEventListener("input", () => {
    if (elements.datasetSizeValue) {
        elements.datasetSizeValue.textContent =
            elements.datasetSize.value;
    }
});

elements.datasetSize?.addEventListener("change", generateRandomNumbers);

elements.sampleButton.addEventListener("click", generateRandomNumbers);
elements.startButton.addEventListener("click", () => runSort({ autoPlay: true }));
elements.pauseButton.addEventListener("click", pauseAnimation);
elements.resumeButton.addEventListener("click", resumeAnimation);
elements.resetButton.addEventListener("click", resetAnimation);
elements.benchmarkButton.addEventListener("click", runBenchmark);

elements.algorithm?.addEventListener("change", () => {
    clearError();
    resetResults();
    stopAnimation();

    events = [];
    currentEventIndex = 0;
    sortedNumbers = [];

    elements.threadLog.replaceChildren();
    elements.threadLegend.replaceChildren();
    elements.timeline.replaceChildren();

    renderBars(originalNumbers);
    renderSortedBars([]);

    elements.stepInfo.textContent =
        `${elements.algorithm.selectedOptions[0].text} сонгогдлоо. Тоглуулах товчийг дарна уу.`;

    elements.startButton.disabled = false;
    elements.pauseButton.disabled = true;
    elements.resumeButton.disabled = true;
    elements.resetButton.disabled = true;
});

window.addEventListener("resize", () => {
    if (lastBenchmark) {
        drawBenchmarkChart(lastBenchmark);
    }
});

const initialValues = [42, 7, 19, 3, 88, 12, 27, 34, 45, 51, 89];

renderBars(initialValues);

if (elements.datasetSizeValue) {
    elements.datasetSizeValue.textContent =
        elements.datasetSize?.value || "12";
}

renderBenchmarkLegend();


document.getElementById('runBtn').addEventListener('click', async () => {
    const rawData = document.getElementById('customInputData').value;

    let requestBody = {};
    if (rawData.trim() !== "") {
        // Хэрэглэгч юм бичсэн бол таслалаар салгаад тоо руу хөрвүүлэх
        const customArray = rawData.split(',').map(item => parseInt(item.trim())).filter(num => !isNaN(num));
        requestBody = { data: customArray };
    } else {
        // Хэрэглэгч хоосон орхисон бол default хэмжээгээр явуулах
        requestBody = { size: 1000 };
    }

    const response = await fetch('/run-benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    });
    const result = await response.json();
    updateChart(result);
});