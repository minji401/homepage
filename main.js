/* ==========================================================================
   1. 하단 갤러리 자동 슬라이드 로직 (무한 루프)
   ========================================================================== */
const galleryWrapper = document.querySelector('.slide-container .slide-wrapper');
const galleryItems = document.querySelectorAll('.slide-container .slide-item');
const galleryItemsToShow = 3; 
const gallerySlideWidth = 460; 

// 앞의 사진들을 복사해서 뒤에 붙이기
for (let i = 0; i < galleryItemsToShow; i++) {
    const clone = galleryItems[i].cloneNode(true);
    galleryWrapper.appendChild(clone);
}

let galleryIndex = 0;
const galleryTotal = galleryItems.length;

function nextGallerySlide() {
    galleryIndex++;
    galleryWrapper.style.transition = 'transform 0.5s ease';
    galleryWrapper.style.transform = `translateX(-${galleryIndex * gallerySlideWidth}px)`;

    if (galleryIndex === galleryTotal) {
        setTimeout(() => {
            galleryWrapper.style.transition = 'none';
            galleryIndex = 0;
            galleryWrapper.style.transform = `translateX(0px)`;
        }, 500);
    }
}
setInterval(nextGallerySlide, 3000);


/* ==========================================================================
   2. 식단표 날짜 변경 로직
   ========================================================================== */
const menus = {
    "5월 9일": ["보리밥", "된장찌개", "제육볶음", "콩나물무침", "깍두기"],
    "5월 10일": ["잡곡밥", "쇠고기 미역국", "고등어 구이", "애호박 나물", "포기 김치"],
    "5월 11일": ["현미밥", "콩나물국", "닭갈비", "시금치나물", "백김치"]
};

let currentDate = 10;
const dateDisplay = document.getElementById('current-date');
const menuList = document.getElementById('menu-list');

document.getElementById('prev-day').addEventListener('click', () => {
    if (currentDate > 9) { currentDate--; updateDiet(); }
});

document.getElementById('next-day').addEventListener('click', () => {
    if (currentDate < 11) { currentDate++; updateDiet(); }
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


/* ==========================================================================
   3. 메인 비주얼 슬라이더 제어 로직 (무한 루프 수정본)
   ========================================================================== */
const sliderWrapper = document.querySelector('.main-slider .slider-wrapper');
const sliderItems = document.querySelectorAll('.main-slider .slider-item');
const slideTotalIndex = sliderItems.length; // 원본 개수 (3)

const btnPrev = document.getElementById('slider-prev');
const btnNext = document.getElementById('slider-next');
const btnToggle = document.getElementById('slider-toggle');
const txtCurrent = document.getElementById('slide-current');
const txtTotal = document.getElementById('slide-total');

// 무한 루프를 위해 첫 번째 슬라이드를 복사하여 맨 뒤에 추가
const firstClone = sliderItems[0].cloneNode(true);
sliderWrapper.appendChild(firstClone);

let slideIndex = 0;
let sliderTimer = null;
let isPlaying = true;
let isTransitioning = false; // 연속 클릭 방지 플래그

if (txtTotal) txtTotal.textContent = slideTotalIndex;

function moveMainSlide(pos) {
    if (isTransitioning) return;
    isTransitioning = true;

    slideIndex = pos;
    sliderWrapper.style.transition = 'transform 0.5s ease-in-out';
    sliderWrapper.style.transform = `translateX(-${slideIndex * 100}%)`;

    // 텍스트 카운터 업데이트
    if (slideIndex >= slideTotalIndex) {
        txtCurrent.textContent = 1;
    } else if (slideIndex < 0) {
        txtCurrent.textContent = slideTotalIndex;
    } else {
        txtCurrent.textContent = slideIndex + 1;
    }
}

// 애니메이션이 완전히 끝난 후 순간이동 처리 (Transition End 이벤트 활용)
sliderWrapper.addEventListener('transitionend', () => {
    isTransitioning = false;

    // 마지막 복사본(4번째)에 도달했을 때 -> 진짜 1번째로 순간이동
    if (slideIndex >= slideTotalIndex) {
        sliderWrapper.style.transition = 'none';
        slideIndex = 0;
        sliderWrapper.style.transform = `translateX(0%)`;
    }
    // 1번째 이전(왼쪽 복사본 생략형 처리)으로 갈 때 -> 진짜 마지막으로 순간이동
    if (slideIndex < 0) {
        sliderWrapper.style.transition = 'none';
        slideIndex = slideTotalIndex - 1;
        sliderWrapper.style.transform = `translateX(-${slideIndex * 100}%)`;
    }
});

// 자동 롤링 제어
function startSliderTimer() {
    if (!sliderTimer) {
        sliderTimer = setInterval(() => { moveMainSlide(slideIndex + 1); }, 3000);
    }
}

function stopSliderTimer() {
    clearInterval(sliderTimer);
    sliderTimer = null;
}

// 버튼 이벤트
btnNext.addEventListener('click', () => {
    if (isPlaying) stopSliderTimer();
    moveMainSlide(slideIndex + 1);
    if (isPlaying) startSliderTimer();
});

btnPrev.addEventListener('click', () => {
    if (isPlaying) stopSliderTimer();
    moveMainSlide(slideIndex - 1);
    if (isPlaying) startSliderTimer();
});

btnToggle.addEventListener('click', () => {
    if (isPlaying) {
        stopSliderTimer();
        btnToggle.innerHTML = '<i class="fas fa-play"></i>';
        isPlaying = false;
    } else {
        startSliderTimer();
        btnToggle.innerHTML = '<i class="fas fa-pause"></i>';
        isPlaying = true;
    }
});

// 최초 실행
startSliderTimer();