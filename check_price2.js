import puppeteer from 'puppeteer';
import axios from 'axios';

// ===== 環境變數設定 =====
const LINE_ACCESS_TOKEN = process.env.LINE_ACCESS_TOKEN;
const TARGET_DEPART = '13:45';
const TARGET_ARRIVE = '13:05';
const PRICE_THRESHOLD = 41000;
const TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&dairport=tpe&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-abc523f1-244d-4275-ae09-2fd3deb41511%5EList-a3bc3d8b-89b8-4386-b257-2eebb0a511a4&shoppingid=SGP_SGP-ALI_PIDReduce-fe7d4a8a-29c0-4ce2-b6b7-6af8c32bcf5b%5EList-e71ea733-b4d7-4752-b48f-a302b01f9bac&groupKey=SGP_SGP-ALI_PIDReduce-fe7d4a8a-29c0-4ce2-b6b7-6af8c32bcf5b%5EList-e71ea733-b4d7-4752-b48f-a302b01f9bac&locale=zh-TW&curr=TWD';

// ===== 解析 time 從 data-testid =====
function extractTimeFromTestid(testid) {
  if (!testid) return '';
  const parts = testid.trim().split(' ');
  return parts.length ? parts[parts.length - 1].slice(0, 5) : '';
}

// ===== 解析價格字串 "NT$41,107" 轉數字 =====
function parsePriceText(text) {
  try {
    return parseInt(text.replace('NT$', '').replace(/,/g, '').trim(), 10);
  } catch {
    return null;
  }
}

// ===== 發送 LINE Notify 訊息 =====
async function sendLineNotification(message) {
  if (!LINE_ACCESS_TOKEN) {
    console.log('⚠️ LINE_ACCESS_TOKEN 未設定，無法發送通知');
    return;
  }
  try {
    const res = await fetch('https://notify-api.line.me/api/notify', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${LINE_ACCESS_TOKEN}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ message }),
    });
    if (res.ok) {
      console.log('✅ 成功發送 LINE 通知');
    } else {
      console.log('❌ 發送通知失敗，狀態碼：', res.status);
    }
  } catch (e) {
    console.log('❌ 發送通知錯誤：', e);
  }
}

async function checkPrice() {
  console.log('🔍 開始查詢 Trip.com...');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();

    // 設定 user-agent，避免被識別成爬蟲
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    console.log('🌐 前往 Trip.com 網頁中...');
    await page.goto(TRIP_URL, { waitUntil: 'networkidle2', timeout: 90000 });

    console.log('⌛ 等待票價資料出現...');
    await page.waitForSelector('[data-price]', { timeout: 90000 });

    console.log('⏳ 等待 JavaScript 完整渲染...');
    await page.waitForTimeout(5000);

    // 取得所有航班卡片
    const cards = await page.$$('.result-item');
    console.log(`✈️ 找到 ${cards.length} 筆航班`);

    let found = false;

    for (const card of cards) {
      try {
        const departTestid = await card.$eval('.is-departure_2a2b .time_cbcc', el => el.getAttribute('data-testid'));
        const arriveTestid = await card.$eval('.is-arrival_f407 .time_cbcc', el => el.getAttribute('data-testid'));
        const departTime = extractTimeFromTestid(departTestid);
        const arriveTime = extractTimeFromTestid(arriveTestid);

        // 從 aria-label 擷取價格
        const priceAria = await card.$eval('.flight-info.is-v2', el => el.getAttribute('aria-label'));
        const priceMatch = priceAria.match(/來回價格：NT\$[\d,]+/);
        let price = null;
        if (priceMatch) {
          price = parsePriceText(priceMatch[0].replace('來回價格：', ''));
        }

        console.log(`📋 出發：${departTime}，抵達：${arriveTime}，票價：${price}`);

        if (departTime === TARGET_DEPART && arriveTime === TARGET_ARRIVE) {
          console.log('✅ 找到符合時間的航班');
          found = true;
          if (price !== null && price <= PRICE_THRESHOLD) {
            console.log('💰 價格也符合條件，將發送通知');
            const msg = `🚨 發現低價票！\n出發：${departTime} OSL\n抵達：${arriveTime} TPE\n票價：${price} 元\n👉 ${TRIP_URL}`;
            await sendLineNotification(msg);
          } else {
            console.log(`⚠️ 價格太高：${price} > ${PRICE_THRESHOLD}，不發送通知`);
          }
          break;
        }
      } catch (e) {
        console.log('⚠️ 某筆航班解析失敗：', e);
      }
    }

    if (!found) {
      console.log('❗ 沒有找到符合條件的航班');
    }

  } catch (e) {
    console.log('🚫 整體錯誤：', e);
    // 如果需要，可以用 page.screenshot() 或 page.content() 來保存錯誤時的狀態
  } finally {
    await browser.close();
    console.log('🧹 Browser 已關閉');
  }
}

checkPrice();
