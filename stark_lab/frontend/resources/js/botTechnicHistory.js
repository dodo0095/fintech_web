const $ = require('jquery');
const axios = require('axios');

console.log('Current Page: botTechnicHistory.html');

const PRELOAD_DURATION = 1;

const handleAxiosGetData = () => {
  const $s3 = $('.s3');
  const $s3Table = $('.s3 .table-list .s3-table-data');
  const $s3TableMobile = $('.s3 .table-list-mobile');
  const $preloader = $('.preloader');

  function _initTableData(apiData) {
    // console.log('apiData', apiData[0]);

    // 桌機平板表格 Append 標題區
    $s3Table.append(`<tr class='data-row data-row-title'>
      ${apiData[0].stock_name ? `<td>股票名稱</td>` : ``}
      ${apiData[0].start_date ? `<td>起始日</td>` : ``}
      ${apiData[0].buy_price ? `<td>買入價格</td>` : ``}
      ${apiData[0].over_date ? `<td>結束日</td>` : ``}
      ${apiData[0].sell_price ? `<td>賣出價格</td>` : ``}
      ${apiData[0].return_value ? `<td>報酬%</td>` : ``}
    </tr>`)


    apiData.forEach(function(item, index) {
      let growType = item.type === `+` ? `increase` : `reduce`;
      // console.log('foreach', item);

      // 桌機平板表格 Append 資料內容
      $s3Table.append(`<tr class='data-row data-row-${index + 1} ${growType}'>
        <td>${item.stock_name}</td>
        <td>${item.start_date}</td>
        <td>${item.buy_price}</td>
        <td>${item.over_date}</td>
        <td>${item.sell_price}</td>
        <td>${item.return_value}%</td>
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
            <td class='data-row-title'>買入價格</td>
            <td>${item.buy_price}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>結束日</td>
            <td>${item.over_date}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>賣出價格</td>
            <td>${item.sell_price}</td>
          </tr>
          <tr class='data-row'>
            <td class='data-row-title'>報酬(%)</td>
            <td>${item.return_value}%</td>
          </tr>
        </table>
      </div>`)
    })
  }


  // Call Api
  axios.get('api/technicHistory/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // Import Value
      _initTableData(RES_DATA);

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