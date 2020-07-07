/* Functions to update and display current time */
function display_c(){
    var refresh=1000; // Refresh rate in milli seconds
    mytime=setTimeout('display_ct()',refresh)
    }
    
function display_ct() {
    var x = new Date()
    document.getElementById('time').innerHTML = x;
    display_c();
}