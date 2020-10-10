const $ = require('jquery');
const axios = require('axios');

console.log('Current Page: bot.html');

const PRELOAD_DURATION = 1;

const handleAxiosGetData = () => {
  const $s2 = $('.s2');
  const $s3 = $('.s3');
  const $s2MonthScore = $('.s2 .score-month');
  const $s2SeasonScore = $('.s2 .score-season');
  const $s2YearScore = $('.s2 .score-year');

  const $s3BasicScore = $('.s3 .content-basic');
  const $s3TechnicScore = $('.s3 .content-technic');

  const $preloader = $('.preloader');

  function _initSection2Data(apiData) {
      $s2MonthScore.find('.score-value-1 .score-value-data').html(`${apiData.monthly_return}%`);
      $s2MonthScore.find('.score-value-2 .score-value-data').html(`${apiData.monthly_0050_return}%`);

      $s2SeasonScore.find('.score-value-1 .score-value-data').html(`${apiData.season_return}%`);
      $s2SeasonScore.find('.score-value-2 .score-value-data').html(`${apiData.season_0050_return}%`);

      $s2YearScore.find('.score-value-1 .score-value-data').html(`${apiData.year_return}%`);
      $s2YearScore.find('.score-value-2 .score-value-data').html(`${apiData.year_0050_return}%`);

      let monthBigger = Math.max(apiData.monthly_return, apiData.monthly_0050_return);
      let seasonBigger = Math.max(apiData.season_return, apiData.season_0050_return);
      let yearBigger = Math.max(apiData.year_return, apiData.year_0050_return);
      // console.log('whoIsBigger', monthBigger, seasonBigger, yearBigger);


      // Init Increase & Reduce
      if (Number(apiData.monthly_return) === monthBigger) {
        $s2MonthScore.find('.score-value-1 .score-value-data').addClass('increase')
      } else {
        $s2MonthScore.find('.score-value-1 .score-value-data').addClass('reduce')
      }

      if (Number(apiData.monthly_0050_return) === monthBigger) {
        $s2MonthScore.find('.score-value-2 .score-value-data').addClass('increase')
      } else {
        $s2MonthScore.find('.score-value-2 .score-value-data').addClass('reduce')
      }

      if (Number(apiData.season_return) === seasonBigger) {
        $s2SeasonScore.find('.score-value-1 .score-value-data').addClass('increase')
      } else {
        $s2SeasonScore.find('.score-value-1 .score-value-data').addClass('reduce')
      }

      if (Number(apiData.season_0050_return) === seasonBigger) {
        $s2SeasonScore.find('.score-value-2 .score-value-data').addClass('increase')
      } else {
        $s2SeasonScore.find('.score-value-2 .score-value-data').addClass('reduce')
      }

      if (Number(apiData.year_return) === yearBigger) {
        $s2YearScore.find('.score-value-1 .score-value-data').addClass('increase')
      } else {
        $s2YearScore.find('.score-value-1 .score-value-data').addClass('reduce')
      }

      if (Number(apiData.year_0050_return) === yearBigger) {
        $s2YearScore.find('.score-value-2 .score-value-data').addClass('increase')
      } else {
        $s2YearScore.find('.score-value-2 .score-value-data').addClass('reduce')
      }
  }

  function _initSection3Data(apiData) {
    $s3BasicScore.find('.score-year .s3-content-score-value').html(`${apiData.fundamental_return}%`);
    $s3BasicScore.find('.score-max .s3-content-score-value').html(`${apiData.fundamental_amplitude}%`);

    $s3TechnicScore.find('.score-year .s3-content-score-value').html(`${apiData.technology_return}%`);
    $s3TechnicScore.find('.score-max .s3-content-score-value').html(`${apiData.technology_amplitude}%`);
  }

  // Call Api
  //axios.get(' http://localhost:8000/api/chose_robot/?format=json')
   axios.get('api/chose_robot/?format=json')
    .then((res) => {
      const RES_DATA = res.data[0];
      console.log('RES_DATA', RES_DATA)
      // const TARGET_DATA = res.data.target;
      // Import Value
      _initSection2Data(RES_DATA);
      _initSection3Data(RES_DATA);

      setTimeout(() => {
        $s2.fadeIn(300);
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
  