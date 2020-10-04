const $ = require('jquery');
const axios = require('axios');
// import $botBlog  from './words/botBlog.json';
console.log('Current Page: botBlog.html');
const PRELOAD_DURATION = 1;
const $navBtn1 = $('.bot-content .s1 .sub-nav .navBtn1');
const $navBtn2 = $('.bot-content .s1 .sub-nav .navBtn2');
const $navBtn3 = $('.bot-content .s1 .sub-nav .navBtn3');
const $navBtn4 = $('.bot-content .s1 .sub-nav .navBtn4');

const handleAxiosGetData = () => {
  // const length = 50;
  // const $s1TableMobile = $('.s1');
  const $s1 = $('.s1');
  const $s1Table = $('.s1 .s1-block .writings-frame');
  // const $s1TableMobile = $('.s1 .s1-block -mobile');
  const $preloader = $('.preloader');

  function _initTableData(apiData) {
    // console.log('apiData', apiData[0]);
    //先清空writings-frame的html，在重新載入API
    document.getElementById('writings-frame').innerHTML = "";
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
        <div class="writings writings-${index + 1}" style="cursor:pointer;" onclick="location.href=
        '${item.link}'">
          <div class="author-frame author${index + 1}">
            <div class="author_picture">
              <img src="${item.author_picture}">
            </div>
            <div class="author-data">
              <div class="author_name">${item.author_name}</div>
              <div class="date">${item.date}</div>
            </div>
          </div>
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
            
          </div>
        </div>
      </div>`)
    })
  }
  




  // Call Api
  // axios.get('//dodo0095.pythonanywhere.com/articleapi/?format=json')
  axios.get('/api/articleapi/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // console.log('Show RES_DATA', RES_DATA);
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success1');
    })
    .catch((error) => {
      console.log('Axios Error', error.message);
    })

  // navBtn1
  $navBtn1.on('click', function() {
    axios.get('/api/articleapi/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // console.log('Show RES_DATA', RES_DATA);
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success1');
    })
    .catch((error) => {
      console.log('Axios Error', error.message);
    })
  });

  // navBtn2
  $navBtn2.on('click', function() {
    axios.get('/api/articleapi2/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // console.log('Show RES_DATA', RES_DATA);
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success2');
    })
    .catch((error) => {
      console.log('Axios Error', error.message);
    })
  });

  // navBtn3
  $navBtn3.on('click', function() {
    axios.get('/api/articleapi/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // console.log('Show RES_DATA', RES_DATA);
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success3');
    })
    .catch((error) => {
      console.log('Axios Error', error.message);
    })
  });

  // navBtn4
  $navBtn4.on('click', function() {
    axios.get('/api/articleapi/?format=json')
    .then((res) => {
      const RES_DATA = res.data;
      // console.log('Show RES_DATA', RES_DATA);
      // Import Value
      _initTableData(RES_DATA);

      setTimeout(() => {
        $s1.fadeIn(300);
        $preloader.addClass('js-hide');
      }, PRELOAD_DURATION);

      console.log('Axios Success4');
    })
    .catch((error) => {
      console.log('Axios Error', error.message);
    })
  });
}

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