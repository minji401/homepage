/* script.js */

// --- 1. 자동 사진 슬라이드 로직 ---
const wrapper = document.querySelector('.slide-wrapper');
const items = document.querySelectorAll('.slide-item');
const itemsToShow = 3; // 한 번에 보여줄 사진 수
const slideWidth = 460; // 이미지 너비 + 간격

// 1. [자동화] 사진 개수에 상관없이 앞의 3장을 복사해서 뒤에 붙이기
for (let i = 0; i < itemsToShow; i++) {
    const clone = items[i].cloneNode(true); // 각 아이템 복사
    wrapper.appendChild(clone); // wrapper의 맨 뒤에 추가
}

let index = 0;
const totalImages = items.length; // 실제 원본 이미지 개수

function nextSlide() {
    index++;
    
    wrapper.style.transition = 'transform 0.5s ease';
    wrapper.style.transform = `translateX(-${index * slideWidth}px)`;

    // 마지막 원본 사진 이후 클론 영역에 도달했을 때
    if (index === totalImages) {
        setTimeout(() => {
            wrapper.style.transition = 'none'; // 애니메이션 끄고
            index = 0; // 순식간에 진짜 1번 위치로 이동
            wrapper.style.transform = `translateX(0px)`;
        }, 500); 
    }
}

setInterval(nextSlide, 3000);

// --- 2. 식단표 날짜 변경 로직 ---
const menus = {
    "5월 9일": ["보리밥", "된장찌개", "제육볶음", "콩나물무침", "깍두기"],
    "5월 10일": ["잡곡밥", "쇠고기 미역국", "고등어 구이", "애호박 나물", "포기 김치"],
    "5월 11일": ["현미밥", "콩나물국", "닭갈비", "시금치나물", "백김치"]
};

let currentDate = 10;
const dateDisplay = document.getElementById('current-date');
const menuList = document.getElementById('menu-list');

document.getElementById('prev-day').addEventListener('click', () => {
    if(currentDate > 9) { currentDate--; updateDiet(); }
});

document.getElementById('next-day').addEventListener('click', () => {
    if(currentDate < 11) { currentDate++; updateDiet(); }
});

function updateDiet() {
    const dateStr = `5월 ${currentDate}일`;
    dateDisplay.innerText = dateStr + (currentDate === 10 ? " (일)" : "");
    menuList.innerHTML = "";
    const dayMenu = menus[dateStr] || ["식단 준비 중"];
    dayMenu.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        menuList.appendChild(li);
    });
}

// --- 3. 메인 비주얼 슬라이더 제어 로직 ---
const sliderWrapper = document.querySelector('.slider-wrapper');
const sliderItems = document.querySelectorAll('.slider-item');
const slideTotalIndex = sliderItems.length;

const btnPrev = document.getElementById('slider-prev');
const btnNext = document.getElementById('slider-next');
const btnToggle = document.getElementById('slider-toggle');
const txtCurrent = document.getElementById('slide-current');
const txtTotal = document.getElementById('slide-total');

let slideIndex = 0;
let sliderTimer = null;
let isPlaying = true; // 자동 재생 상태 여부 변수

// 전체 개수 설정 초기화
if (txtTotal) txtTotal.textContent = slideTotalIndex;

// 슬라이드 이동 및 번호 업데이트 함수
function moveMainSlide(pos) {
    slideIndex = pos;
    
    // 범위를 벗어나지 않도록 안전장치 처리
    if (slideIndex >= slideTotalIndex) slideIndex = 0;
    if (slideIndex < 0) slideIndex = slideTotalIndex - 1;
    
    // 이동 시키기
    sliderWrapper.style.transform = `translateX(-${slideIndex * 100}%)`;
    
    // 현재 몇 번째 인지 글자 바꾸기 (0부터 시작하므로 +1)
    txtCurrent.textContent = slideIndex + 1;
}

// 자동 롤링 시작 함수
function startSliderTimer() {
    sliderTimer = setInterval(() => {
        moveMainSlide(slideIndex + 1);
    }, 3000); // 3초마다 다음 사진으로 이동
}

// 자동 롤링 정지 함수
function stopSliderTimer() {
    clearInterval(sliderTimer);
}

// 다음 / 이전 버튼 이벤트 걸기
btnNext.addEventListener('click', () => {
    moveMainSlide(slideIndex + 1);
});

btnPrev.addEventListener('click', () => {
    moveMainSlide(slideIndex - 1);
});

// 중앙 일시정지 및 재생 버튼 (토글 기능)
btnToggle.addEventListener('click', () => {
    if (isPlaying) {
        // 재생 중일 때 누르면 -> 멈춤
        stopSliderTimer();
        btnToggle.innerHTML = '<i class="fas fa-play"></i>'; // 아이콘 재생 모양으로 변경
        isPlaying = false;
    } else {
        // 멈춰있을 때 누르면 -> 다시 재생
        startSliderTimer();
        btnToggle.innerHTML = '<i class="fas fa-pause"></i>'; // 아이콘 일시정지 모양으로 변경
        isPlaying = true;
    }
});

// 페이지가 로드되면 최초로 자동 롤링 실행 시작
startSliderTimer();