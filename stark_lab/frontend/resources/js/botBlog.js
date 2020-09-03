const $ = require('jquery');
const axios = require('axios');
// import $botBlog  from './words/botBlog.json';
console.log('Current Page: botBlog.html');
const PRELOAD_DURATION = 1;



const handleAxiosGetData = () => {
  // const length = 50;
  const $s1TableMobile = $('.s1');
  const $s1Table = $('.s1 .s1-block .writings-frame');
  // const $s1TableMobile = $('.s1 .s1-block -mobile');
  const $preloader = $('.preloader');

  function _initTableData(apiData) {
    // console.log('apiData', apiData[0]);

    // 桌機平板表格 Append 標題區
    // $s1Table.append(`<tr class='data-row data-row-title'>
    //   ${apiData[0].stock_name ? `<td>股票名稱</td>` : ``}
    //   ${apiData[0].start_date ? `<td>起始日</td>` : ``}
    //   ${apiData[0].buy_price ? `<td>買入價格</td>` : ``}
    //   ${apiData[0].over_date ? `<td>結束日</td>` : ``}
    //   ${apiData[0].sell_price ? `<td>賣出價格</td>` : ``}
    //   ${apiData[0].return_value ? `<td>報酬%</td>` : ``}
    // </tr>`)


    apiData.forEach(function(item, index) {
      // let growType = item.type === `+` ? `increase` : `reduce`;
      // console.log('foreach', item);
      // $s1Table.append(`<tr class='writings writings-${index + 1} ${growType}'>

      

      // const ellipsis = item.abstract;
      // ellipsis.forEach((item) => {
      //   if(item.innerHTML.length > length) {
      //     let txt = item.innerHTML.substring(0, length) + '...';
      //     item.innerHTML = txt;
      //   }
      // }
      // 桌機平板表格 Append 資料內容
      $s1Table.append(`
      <div class='writings-frame'>
        <div class='writings writings-${index + 1}'>
          <div class='title_picture title_picture${index + 1}'>
            <figure>
              <img src="${item.title_picture}">
            </figure>

            <div class="title title${index + 1}">
              <h3>${item.title}</h3>
            </div>
            <div class="abstract abstract${index + 1}">
              <span>${item.abstract}</span>
            </div>
            <div class="author-frame author${index + 1}">
              <div class="author_picture">
                <img src="${items.author_picture}">
              </div>
            <div class="author-data">
              <div class="author_name">${items.author_name}</div>
              <div class="date">${items.date}</div>
            </div>
          </div>
        </div>
      </div>`)
    })
  }
    //   $s1TableMobile.append(`<div class='table-list-nav list-nav-${index + 1}'>
    //     <table cellspacing='6' class='${growType}'>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>股票名稱</td>
    //         <td>${item.stock_name}</td>
    //       </tr>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>起始日</td>
    //         <td>${item.start_date}</td>
    //       </tr>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>買入價格</td>
    //         <td>${item.buy_price}</td>
    //       </tr>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>結束日</td>
    //         <td>${item.over_date}</td>
    //       </tr>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>賣出價格</td>
    //         <td>${item.sell_price}</td>
    //       </tr>
    //       <tr class='data-row'>
    //         <td class='data-row-title'>報酬(%)</td>
    //         <td>${item.return_value}%</td>
    //       </tr>
    //     </table>
    //   </div>`)
    // })
  }


  // Call Api
  axios.get('./words/botBlog.json')
    .then((res) => {
      const RES_DATA = res.data;
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success');
    })
    .catch((error) => {
      console.log('Axios Error');
    })


handleAxiosGetData();



// $(function(){
//   var len = 10;
//   $(".JQellipsis").each(function(i){
//       if($(this).text().length>len){
//           $(this).attr("title",$(this).text());
//           var text=$(this).text().substring(0,len-1)+"...";
//           $(this).text(text);
//       }
//   });
// });