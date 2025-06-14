import puppeteer from 'puppeteer';
import fetch from 'node-fetch';
import fs from 'fs/promises';

const LINE_ACCESS_TOKEN = process.env.LINE_ACCESS_TOKEN;
const TARGET_DEPART = '13:45';
const TARGET_ARRIVE = '13:05';
const PRICE_THRESHOLD = 41000;

// 模擬 waitForTimeout 的函數
const waitForTimeout = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function extractTimeFromTestid(testid) {
  if (!testid) return '';
  const parts = testid.trim().split(' ');
  return parts.length ? parts[parts.length - 1].slice(0, 5) : '';
}

function parsePriceText(text) {
  try {
    return parseInt(text.replace('NT$', '').replace(/,/g, '').trim(), 10);
  } catch {
    return null;
  }
}

async function sendLineNotification(message) {
  if (!LINE_ACCESS_TOKEN) {
    console.log('⚠️ LINE_ACCESS_TOKEN 未設定，無法發送通知');
    return;
  }
  try {
    const res = await fetch('https://notify-api.line.me/api/notify', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${LINE_ACCESS_TOKEN}`,
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

  let page;
  try {
    page = await browser.newPage();

    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );

    console.log('🌐 前往 Trip.com 首頁...');
    await page.goto('https://tw.trip.com/flights', {
      waitUntil: 'networkidle2',
      timeout: 60000,
    });

    // 等待出發機場輸入框出現
    await page.waitForSelector('input[data-testid="search_city_from0"]', { timeout: 30000 });
    console.log('✅ 出發機場輸入框已加載');
    await page.click('input[data-testid="search_city_from0"]');
    await page.keyboard.type('Taipei');
    await waitForTimeout(1000);
    await page.keyboard.press('Enter');
    console.log('✅ 出發機場輸入完成');

    // 等待抵達機場輸入框出現
    await page.waitForSelector('input[data-testid="search_city_to0"]', { timeout: 30000 });
    console.log('✅ 抵達機場輸入框已加載');
    await page.click('input[data-testid="search_city_to0"]');
    await page.keyboard.type('Oslo');
    await waitForTimeout(1000);
    await page.keyboard.press('Enter');
    console.log('✅ 抵達機場輸入完成');

    // 等待出發日期輸入框出現
    await page.waitForSelector('input[data-testid="search_date_depart0"]', { timeout: 30000 });
    console.log('✅ 出發日期輸入框已加載');
    await page.click('input[data-testid="search_date_depart0"]');
    await waitForTimeout(500);
    await page.evaluate(() => {
      const target = document.querySelector('[aria-label="2025年9月27日"]');
      if (target) target.click();
    });
    console.log('✅ 出發日期選擇完成');

    // 等待回程日期輸入框出現
    await page.waitForSelector('input[data-testid="search_date_return0"]', { timeout: 30000 });
    console.log('✅ 回程日期輸入框已加載');
    await page.click('input[data-testid="search_date_return0"]');
    await waitForTimeout(500);
    await page.evaluate(() => {
      const target = document.querySelector('[aria-label="2025年10月11日"]');
      if (target) target.click();
    });
    console.log('✅ 回程日期選擇完成');

    // 等待搜尋按鈕出現
    await page.waitForSelector('div[data-testid="search_btn"]', { timeout: 30000 });
    console.log('🔍 提交搜尋條件...');
    await page.click('div[data-testid="search_btn"]');
    console.log('✅ 搜尋按鈕已點擊');

    // 等待搜尋結果出現
    console.log('⌛ 等待搜尋結果...');
    try {
      await page.waitForSelector('[data-price]', { timeout: 120000 });
      console.log('✅ 搜尋結果已加載');
    } catch (e) {
      console.log('⚠️ 搜尋結果未加載，檢查是否有「無結果」或錯誤訊息...');
      // 檢查是否有「無結果」或錯誤訊息
      const noResults = await page.$('.no-result, .error-message, [data-testid="no-results"]');
      if (noResults) {
        const message = await page.evaluate(el => el.textContent, noResults);
        console.log(`❌ 頁面顯示：${message}`);
        await fs.writeFile('error_page.html', await page.content());
        console.log('📄 頁面 HTML 已保存至 error_page.html');
        return;
      }
      throw e; // 如果沒有無結果訊息，拋出原始錯誤
    }

    await waitForTimeout(5000); // 額外等待確保結果穩定

    const cards = await page.$$('.result-item');
    console.log(`✈️ 找到 ${cards.length} 筆航班`);

    let found = false;

    for (const card of cards) {
      try {
        const departTestid = await card.$eval('.is-departure_2a2b .time_cbcc', el =>
          el.getAttribute('data-testid')
        );
        const arriveTestid = await card.$eval('.is-arrival_f407 .time_cbcc', el =>
          el.getAttribute('data-testid')
        );
        const departTime = extractTimeFromTestid(departTestid);
        const arriveTime = extractTimeFromTestid(arriveTestid);

        const priceAria = await card.$eval('.flight-info.is-v2', el =>
          el.getAttribute('aria-label')
        );
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
            const now = new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
            const msg = `🚨 發現低價票！\n出發：${departTime} OSL\n抵達：${arriveTime} TPE\n票價：${price} 元\n查詢時間：${now}\n🔗 https://tw.trip.com/flights`;
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
    // 僅在 page 存在時保存截圖和 HTML
    if (page) {
      await page.screenshot({ path: 'error_screenshot.png' });
      console.log('📸 錯誤截圖已保存');
      await fs.writeFile('error_page.html', await page.content());
      console.log('📄 頁面 HTML 已保存至 error_page.html');
    } else {
      console.log('⚠️ page 未定義，無法保存截圖和 HTML');
    }
  } finally {
    await browser.close();
    console.log('🧹 Browser 已關閉');
  }
}

checkPrice();