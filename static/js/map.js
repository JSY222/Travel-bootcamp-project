// HTML 요소 선택
const $ = (selector) => document.querySelector(selector);

// 대한민국 지도 생성
const map = L.map("map", {
    center: [36.3, 127.8],
    zoom: 7,
    minZoom: 6,
    maxZoom: 13
});

// 지도 배경
L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


// 사용할 14개 지역
const TARGET_REGIONS = [
    "경상북도", "경상남도",
    "전라북도", "전라남도",
    "제주특별자치도", "강원도",
    "충청북도", "충청남도",
    "경기도", "서울특별시",
    "대구광역시", "부산광역시",
    "광주광역시", "인천광역시"
];

// 지역별 지도 중심점
const REGION_CENTERS = {
    "경상북도": [36.4, 128.7],
    "경상남도": [35.35, 128.2],
    "전라북도": [35.7, 127.1],
    "전라남도": [34.9, 126.9],
    "제주특별자치도": [33.4, 126.55],
    "강원도": [37.7, 128.2],
    "충청북도": [36.7, 127.7],
    "충청남도": [36.5, 126.9],
    "경기도": [37.4, 127.1],
    "서울특별시": [37.5665, 126.978],
    "대구광역시": [35.8714, 128.6014],
    "부산광역시": [35.1796, 129.0756],
    "광주광역시": [35.1595, 126.8526],
    "인천광역시": [37.4563, 126.7052]
};

// 옛 이름과 현재 이름을 비교하기 위한 함수
function normalizeName(name) {
    const aliases = {
        "전북특별자치도": "전라북도",
        "강원특별자치도": "강원도",
        "제주도": "제주특별자치도"
    };

    return aliases[name] || name;
}

// 지도에 표시할 데이터
let regions = [];
let regionLayer = null;
let divisionLayer = null;
let selectedRegion = null;

// 외부 행정구역 GeoJSON
const PROVINCE_GEOJSON =
    "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/gadm/json/skorea-provinces-geo.json";

const MUNICIPALITY_GEOJSON =
    "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/gadm/json/skorea-municipalities-geo.json";

let provinceGeojson = null;
let municipalityGeojson = null;


// 상태 메시지
function setStatus(message) {
    $("#statusMessage").textContent = message;
}


// Flask API에서 JSON 데이터 받기
async function getJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP 오류: ${response.status}`);
    }

    const data = await response.json();

    if (data.ok === false) {
        throw new Error(data.error || "데이터 조회 실패");
    }

    return data;
}


// 지역 이름을 GeoJSON과 연결
function getProvinceName(feature) {
    const p = feature.properties || {};

    const names = {
        "Seoul": "서울특별시",
        "Busan": "부산광역시",
        "Daegu": "대구광역시",
        "Incheon": "인천광역시",
        "Gwangju": "광주광역시",
        "Daejeon": "대전광역시",
        "Ulsan": "울산광역시",
        "Gyeonggi-do": "경기도",
        "Gangwon-do": "강원도",
        "Chungcheongbuk-do": "충청북도",
        "Chungcheongnam-do": "충청남도",
        "Jeollabuk-do": "전라북도",
        "Jeollanam-do": "전라남도",
        "Gyeongsangbuk-do": "경상북도",
        "Gyeongsangnam-do": "경상남도",
        "Jeju-do": "제주특별자치도"
    };

    const raw = p.NAME_1 || p.name || p.NAME || "";

    return names[raw] || normalizeName(raw);
}


// 1. 처음 지역 데이터 불러오기
async function loadRegions() {
    try {
        setStatus("지역 정보를 불러오는 중...");

        const [dbData, geoData] = await Promise.all([
            getJSON("/api/regions"),
            fetch(PROVINCE_GEOJSON).then(res => {
                if (!res.ok) {
                    throw new Error("지도 경계 데이터 로드 실패");
                }
                return res.json();
            })
        ]);

        regions = dbData.regions.filter(region =>
            TARGET_REGIONS.includes(
                normalizeName(region.name)
            )
        );

        provinceGeojson = geoData;

        drawRegions();
        createRegionButtons();

        setStatus("지도에서 원하는 지역을 클릭하세요.");

    } catch (error) {
        console.error(error);
        setStatus("오류: " + error.message);
    }
}


// 2. 대한민국 지도에 지역 표시
function drawRegions() {
    if (regionLayer) {
        map.removeLayer(regionLayer);
    }

    regionLayer = L.geoJSON(provinceGeojson, {
        filter: function(feature) {
            const name = getProvinceName(feature);

            return regions.some(
                region =>
                    normalizeName(region.name) === name
            );
        },

        style: {
            color: "#ffffff",
            weight: 2,
            fillColor: "#71a5d8",
            fillOpacity: 0.45
        },

        onEachFeature: function(feature, layer) {
            const name = getProvinceName(feature);

            const region = regions.find(
                r => normalizeName(r.name) === name
            );

            if (!region) return;

            layer.bindTooltip(region.name, {
                permanent: true,
                direction: "center",
                className: "region-label"
            });

            layer.on("mouseover", function() {
                layer.setStyle({
                    fillColor: "#2478c5",
                    fillOpacity: 0.65
                });
            });

            layer.on("mouseout", function() {
                regionLayer.resetStyle(layer);
            });

            layer.on("click", function() {
                selectRegion(region, layer);
            });
        }
    }).addTo(map);

    if (regionLayer.getLayers().length > 0) {
        map.fitBounds(regionLayer.getBounds(), {
            padding: [25, 25]
        });
    }
}


// 3. 지역 버튼 생성
function createRegionButtons() {
    const container = $("#regionList");
    container.replaceChildren();

    regions.forEach(region => {
        const button = document.createElement("button");

        button.className = "region-button";
        button.textContent = region.name;

        button.addEventListener("click", () => {
            const layer = regionLayer.getLayers().find(
                item =>
                    getProvinceName(item.feature) ===
                    normalizeName(region.name)
            );

            selectRegion(region, layer);
        });

        container.appendChild(button);
    });
}


// 4. 지역 선택 및 확대
async function selectRegion(region, layer) {
    try {
        selectedRegion = region;

        $("#mapTitle").textContent = region.name;
        $("#listTitle").textContent = region.name + " 시·군·구";
        $("#backBtn").hidden = false;

        $("#regionList").hidden = true;
        $("#divisionList").hidden = false;

        if (layer) {
            map.fitBounds(layer.getBounds(), {
                padding: [35, 35],
                maxZoom: 10
            });
        } else {
            const center =
                REGION_CENTERS[normalizeName(region.name)];

            if (center) {
                map.setView(center, 9);
            }
        }

        const data = await getJSON(
            `/api/regions/${region.id}/divisions`
        );

        createDivisionButtons(data.divisions);

        await drawDivisions(region, data.divisions);

        setStatus(
            `${region.name}: ${data.divisions.length}개 시·군·구 조회`
        );

    } catch (error) {
        console.error(error);
        setStatus("오류: " + error.message);
    }
}


// 5. 시군구 버튼 생성
function createDivisionButtons(divisions) {
    const container = $("#divisionList");
    container.replaceChildren();

    divisions.forEach(division => {
        const button = document.createElement("button");

        button.className = "division-button";
        button.textContent = division.name;

        button.addEventListener("click", () => {
            zoomToDivision(division.name);
        });

        container.appendChild(button);
    });
}


// 6. 시군구 경계 표시
async function drawDivisions(region, divisions) {
    if (divisionLayer) {
        map.removeLayer(divisionLayer);
        divisionLayer = null;
    }

    if (!municipalityGeojson) {
        const response = await fetch(MUNICIPALITY_GEOJSON);

        if (!response.ok) {
            throw new Error("시군구 경계 자료를 가져오지 못했습니다.");
        }

        municipalityGeojson = await response.json();
    }

    const provinceName = normalizeName(region.name);

    const names = new Set(
        divisions.map(d => d.name)
    );

    // 구형 경계 자료의 지역 이름을 비교
    divisionLayer = L.geoJSON(municipalityGeojson, {
        filter: function(feature) {
            const p = feature.properties || {};

            const parent = getProvinceName(feature);
            const divisionName = p.NAME_2 || p.name || "";

            return parent === provinceName &&
                   names.has(divisionName);
        },

        style: {
            color: "#2463a0",
            weight: 1.5,
            fillColor: "#a9d2f2",
            fillOpacity: 0.4
        },

        onEachFeature: function(feature, layer) {
            const name =
                feature.properties.NAME_2 ||
                feature.properties.name ||
                "";

            layer.bindTooltip(name, {
                permanent: true,
                direction: "center",
                className: "region-label"
            });
        }
    }).addTo(map);
}


// 7. 시군구 버튼 클릭 시 확대
function zoomToDivision(name) {
    if (!divisionLayer) return;

    const layer = divisionLayer.getLayers().find(
        item =>
            (item.feature.properties.NAME_2 ||
             item.feature.properties.name) === name
    );

    if (layer) {
        map.fitBounds(layer.getBounds(), {
            padding: [40, 40],
            maxZoom: 12
        });
    } else {
        setStatus(
            `${name}: 현재 경계 자료에서 위치를 찾지 못했습니다.`
        );
    }
}


// 8. 전체 지도로 돌아가기
function goBack() {
    selectedRegion = null;

    $("#mapTitle").textContent = "대한민국 전체";
    $("#listTitle").textContent = "지역 목록";
    $("#backBtn").hidden = true;

    $("#regionList").hidden = false;
    $("#divisionList").hidden = true;

    if (divisionLayer) {
        map.removeLayer(divisionLayer);
        divisionLayer = null;
    }

    if (regionLayer) {
        regionLayer.addTo(map);

        map.fitBounds(regionLayer.getBounds(), {
            padding: [25, 25]
        });
    }

    setStatus("지도에서 원하는 지역을 클릭하세요.");
}


// 뒤로가기 버튼 이벤트
$("#backBtn").addEventListener("click", goBack);

// 첫 실행
$("#divisionList").hidden = true;
loadRegions();