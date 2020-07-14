const $ = require('jquery');
const axios = require('axios');

console.log('Current Page: botBasicHistory.html');

const PRELOAD_DURATION = 1000;

const handleAxiosGetData = () => {
  const $s3 = $('.s3');
  const $s3Table = $('.s3 .table-list .s3-table-data');
  const $s3TableMobile = $('.s3 .table-list-mobile');
  const $s3TableTime = $('.s3 .s3-date-time');

  const $s3BoardToday = $('.s3 .board-today');
  const $s3BoardTotal = $('.s3 .board-total');

  const $preloader = $('.preloader');

  function _initTableData(apiData) {
    // console.log('apiData', apiData[0]);
    // 桌機平板表格 Append 標題區
    $s3Table.append(`<tr class='data-row data-row-title'>
      ${apiData[0].stock_name ? `<td>股票名稱</td>` : ``}
      ${apiData[0].start_date ? `<td>起始日</td>` : ``}
      ${apiData[0].start_price ? `<td>起始價</td>` : ``}
      ${apiData[0].current_price ? `<td>昨日收盤價</td>` : ``}
      ${apiData[0].over_date ? `<td>預計結束日</td>` : ``}
      ${apiData[0].now_return ? `<td>至今漲幅</td>` : ``}
    </tr>`)


    apiData.forEach(function(item, index) {
      let growType = item.type === `+` ? `increase` : `reduce`;
      // console.log('foreach', item);

      // 桌機平板表格 Append 資料內容
      $s3Table.append(`<tr class='data-row data-row-${index + 1} ${growType}'>
        <td>${item.stock_name}</td>
        <td>${item.start_date}</td>
        <td>${item.start_price}</td>
        <td>${item.current_price}</td>
        <td>${item.over_date}</td>
        <td>${item.now_return}</td>
      </tr>`)

      $s3TableMobile.append(`<div class='table-list-nav list-nav-${index + 1}'>
        <table cellspacing='6' class='${growType}'>
          <tr class='data-row'>
            <td class='data-row-title'>股票名稱</td>
            <td>${item.stock_name}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>起始日</td>
            <td>${item.start_date}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>起始價</td>
            <td>${item.start_price}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>昨日收盤價</td>
            <td>${item.current_price}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>預計結束日</td>
            <td>${item.over_date}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>至今漲幅</td>
            <td>${item.now_return}</td>
          </tr>
        </table>
      </div>`)
    })
  }

  function _initBoardValue(apiData) {
    $s3BoardToday.find('.board-nav-value-count').text(apiData.today);
    $s3BoardTotal.find('.board-nav-value-count').text(apiData.total);

    if (apiData.today[0].includes('-')) {
      $s3BoardToday.addClass('reduce');
    } else {
      $s3BoardToday.addClass('increase');
    }

    if (apiData.total[0].includes('-')) {
      $s3BoardTotal.addClass('reduce');
    } else {
      $s3BoardTotal.addClass('increase');
    }

  }

  function _initTableTime(apiData) {
    $s3TableTime.text(apiData);
  }


  // Call Api
  axios.get('/basicCurrent/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // Import Value
      _initTableData(RES_DATA.final_update);
      _initTableTime(RES_DATA.tableTime);
      _initBoardValue(RES_DATA.board)

      setTimeout(() => {
        $s3.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success');
    })
    .catch((error) => {
      console.log('Axios Error');
    })
}

handleAxiosGetData();