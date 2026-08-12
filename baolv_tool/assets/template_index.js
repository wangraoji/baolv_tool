
// 刷怪间隔是否显示"实际"换算形式 (由生成器注入)
let MON_GEN_TIME_REAL = true;

const App = {
    data() {
        return {
            loading: false,
            isNotJs: false,
            description: "",
            menuList: [
                {
                    label: "物品查询",
                    code: "item",
                    placeholder: "输入 物品名称",
                },
                {
                    label: "怪物查询",
                    code: "mon",
                    placeholder: "输入 怪物名称",
                },
                {
                    label: "地图查询",
                    code: "map",
                    placeholder: "输入 地图名称或者编号，地图编号[地图名称]",
                },
                {
                    label: "NPC查询",
                    code: "npc",
                    placeholder: "输入 NPC名称",
                },
                {
                    label: "版本攻略",
                    code: "help",
                    placeholder: "...",
                },
            ],
            cutMenu: "item",
            placeholder: "",
            // 搜索
            keyVal: "",
            /**
             *********************************** 物品菜单
             */
            // 数据库Item
            itemsDb: {},
            newItems: [],
            // 所有物品
            itemList: [],
            // 选中物品
            selectItem: {},
            // 物品产出
            itemOutputList: [],
            // 物品产出选中
            selectItemOutput: "",
            /**
             *********************************** 怪物菜单
             */
            // 所有怪物
            monList: [],
            // 选中怪物
            selectMon: "",
            // 怪物产出
            monOutputList: [],
            /**
             *********************************** 刷怪列表
             */
            monGenList: [],
            /**
             *********************************** 地图菜单
             */
            mapInfoObj: {},
            allMapInfo: {},
            // 选中的地图
            selectMap: {},
            // 地图怪物列表
            mapMonList: [],
            // 地图Npc列表
            mapNpcList: [],
            // 地图走法
            mapGoInfo: [],
            // 地图上级入口数据库
            mapGoDb: [],
            // NPC 脚本地图入口
            mapNpcGoList: [],
            /**
             *********************************** NPC菜单
            */
            npcList: [],
            /** 是否可以双击打开查看怪物爆率 */
            isDbClickMon: true,
            /** JS加载时间 */
            loadJsTime: 3000,
            /**
             * 物品查询相关参数
             */
            // 1 全部物品， 2 能查到爆率的物品， 3 开放给玩家自己选择
            itemQueryType: 3,
            itemQueryList: [
                {
                    label: "全部物品",
                    value: 1
                },
                {
                    label: "有出处的物品",
                    value: 2
                },
            ],

            /**
            * 怪物查询相关参数
            */
            // 1 全部怪物， 2 能查到有产出的怪， 3 能查到有产出且有刷新地的怪， 4 开放给玩家选择
            monQueryType: 4,
            monQueryList: [
                {
                    label: "全部怪物",
                    value: 1
                },
                {
                    label: "有产出的怪",
                    value: 2
                },
                {
                    label: "有产出且或有刷新地的怪",
                    value: 3
                },
            ],

            /**
             * 地图查询相关参数
             */
            // 1 全部地图， 2 能查到有怪物或NPC的地图， 3 开放给玩家自己选择
            mapQueryType: 3,
            mapQueryList: [
                {
                    label: "全部地图",
                    value: 1
                },
                {
                    label: "有怪物或NPC的地图",
                    value: 2
                },
            ],
            // 默认使用 全部
            defaultQueryUse: {
                item: 1,
                mon: 1,
                map: 1
            },
            // 攻略是否显示
            gonglveShow: true,
            // 攻略内容
            gonglveContent: `PS：宝宝打死好像不加币。

没有充值货币。（免费游戏，不做充值）.  

不要越级打怪，上线领礼包直接下新手地图

福利币：高于50血（防刷稻草人、魔幻蜘蛛）的怪必加！低于50血的不加。所以刷币推荐打一下能秒的怪！

白嫖助手-货币兑换  -福利币换所有货币。其他货币兑换在顶部货币兑换按钮

白嫖助手-爆率提升-无上限，有打怪点无脑提升。能提多高提多高。后期货币用不完了，福利币可以买打怪点。


动态刷怪说明：超过60分钟的BOSS都调整成为60（实际刷新为4倍，也就是15分钟刷新）分钟
低于60（部分BOSS除外）分钟刷新的怪，地图怪物低于一定的数量会自动刷新，无需等待固定时间。
高于60分钟刷新的怪，不受动态刷怪影响为系统刷怪，需要指定的时间刷新。

兑换码：666888

额外提示：免费游戏攻速统一，所以攻略说的攻速无效。
上线默认300%攻速！人人攻速一样。避免有人开挂无限刀。遇到直接录屏举报即可。

进地图20秒不刷怪，说明这个地图是BOSS地图，只刷60（实际刷新为4倍，也就是15分钟刷新）分钟以上的。
不确定是不是BOSS地图：白嫖助手-综合服务-查询系统-地图搜索-可以看当前地图刷怪、坐标、时间等。
`,
            // 是否显示怪物刷新所在地图的坐标、范围、数量、时间
            isShowMonGenInfo: true,
            // 网站标题
            webTitle:`双生觉醒查询系统`,
        };
    },
    mounted() {
        this.placeholder = this.menuList[0].placeholder;
        // 归一化 merchant 分隔符: 兼容 GOM(tab分隔+反斜杠) 与 LF(空格分隔+竖线)
        if (typeof merchant !== "undefined") {
            merchant = merchant.map(row => {
                let r = row.replace(/\\/g, "|");
                if (r.indexOf("\t") != -1) {
                    r = r.replace(/\t+/g, " ").replace(/\s+/g, " ").trim();
                }
                return r;
            });
        }
        this.formatMapGoDb();
        this.formatItems();
        this.getItemList();
        this.getMapInfoObj();
        this.allMapInfo = {};
        for (const key in mapInfo) {
            if (Object.hasOwnProperty.call(mapInfo, key)) {
                const element = mapInfo[key];
                this.allMapInfo[key.toUpperCase()] = element;
            }
        };
    },
    methods: {
        initJsFields() {
            this.loading = true;
            let timeStr = new Date().getTime();
            let itemsJS = document.createElement("script");
            itemsJS.src = "./items.js?v=" + timeStr;
            let monOutputJS = document.createElement("script");
            monOutputJS.src = "./monOutput.js?v=" + timeStr;
            let monsJS = document.createElement("script");
            monsJS.src = "./mons.js?v=" + timeStr;
            let monGenJS = document.createElement("script");
            monGenJS.src = "./monGen.js?v=" + timeStr;
            let mapInfoJS = document.createElement("script");
            mapInfoJS.src = "./mapInfo.js?v=" + timeStr;
            let merchantJS = document.createElement("script");
            merchantJS.src = "./merchant.js?v=" + timeStr;
            let mapGoJS = document.createElement("script");
            mapGoJS.src = "./mapGo.js?v=" + timeStr;
            document.querySelector("head").appendChild(itemsJS)
            document.querySelector("head").appendChild(monOutputJS)
            document.querySelector("head").appendChild(monsJS)
            document.querySelector("head").appendChild(monGenJS)
            document.querySelector("head").appendChild(mapInfoJS)
            document.querySelector("head").appendChild(mapGoJS)
            document.querySelector("head").appendChild(merchantJS)

            setTimeout(() => {
                if (typeof (items) == "undefined" || items == null) {
                    this.$message.error("items.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "items.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (monOutput) == "undefined" || monOutput == null) {
                    this.$message.error("monOutput.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "monOutput.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (mons) == "undefined" || mons == null) {
                    this.$message.error("mons.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "mons.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (mongen) == "undefined" || mongen == null) {
                    this.$message.error("mongen.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "mongen.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (mapInfo) == "undefined" || mapInfo == null) {
                    this.$message.error("mapInfo.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "mapInfo.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (merchant) == "undefined" || merchant == null) {
                    this.$message.error("merchant.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "merchant.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                if (typeof (mapGo) == "undefined" || mapGo == null) {
                    this.$message.error("mapGoJS.js没有找到，或者数据异常。")
                    this.loading = false;
                    this.isNotJs = true;
                    this.description = "mapGoJS.js没有找到，或者数据异常。请尝试刷新页面获取，如果反复刷新几次都是这样请联系管理。"
                    return
                }
                this.formatMapGoDb();
                this.formatItems();
                this.getItemList();
                this.getMapInfoObj();
                this.allMapInfo = {};
                for (const key in mapInfo) {
                    if (Object.hasOwnProperty.call(mapInfo, key)) {
                        const element = mapInfo[key];
                        this.allMapInfo[key.toUpperCase()] = element;
                    }
                };
                this.loading = false;
            }, this.loadJsTime);
        },
        changeItem(item) {
            this.cutMenu = item.code;
            this.placeholder = item.placeholder
            this.keyVal = "";
            this.monGenList = [];
            if (item.code == 'item') {
                this.getItemList();
                if (this.selectItemOutput) {
                    this.getMonGenList(this.selectItemOutput)
                }

            } else if (item.code == 'mon') {
                this.getMonList();
                if (this.selectMon) {
                    this.getMonGenList(this.selectMon)
                }
            } else if (item.code == 'map') {
                this.getMapInfoObj()
            } else if (item.code == 'npc') {
                this.getNpcList()
            } else {
                // ...
            }
        },
        // 搜索触发
        toFilterData() {
            if (this.cutMenu == 'item') {
                this.getItemList(this.keyVal)
            }
            if (this.cutMenu == 'mon') {
                this.getMonList(this.keyVal)
            }
            if (this.cutMenu == 'map') {
                this.getMapInfoObj(this.keyVal)
            }
            if (this.cutMenu == 'npc') {
                this.getNpcList(this.keyVal)
            }
        },


        /**
         *************************************** 物品
         */
        // 选中物品触发
        selectItemFn(item) {
            if (this.selectItem.value == item.value) {
                this.selectItem = {}
            } else {
                this.selectItem = item;
            }
            this.selectItemOutput = "";
            this.getMonGenList(this.selectItemOutput)
            // 获取物品产出
            this.getItemOutput()
        },
        // 格式化物品
        formatItems() {
            this.newItems = [];
            this.itemsDb = items;
            for (const key in items) {
                if (Object.hasOwnProperty.call(items, key)) {
                    const element = items[key];
                    this.newItems.push({
                        key: key,
                        value: element
                    })
                }
            }
        },
        // 获取物品列表
        getItemList(val) {
            this.loading = true;
            if (this.defaultQueryUse.item == 1) {
                this.itemList = this.newItems.filter(el => val ? el.value.indexOf(val) != -1 : el)
            } else {
                let findMonOutput = JSON.stringify(monOutput);
                let tempItemList = this.newItems.filter(el => val ? el.value.indexOf(val) != -1 : el);
                this.itemList = tempItemList.filter(el => findMonOutput.indexOf('"' + el.key + ',') != -1 || findMonOutput.indexOf(',' + el.key + ',') != -1 || findMonOutput.indexOf(',' + el.key + '"') != -1)
            }
            setTimeout(() => {
                this.loading = false;
            }, 200);
        },
        // 获取物品产出
        getItemOutput() {
            if (!this.selectItem.value) {
                this.itemOutputList = [];
                return
            }
            this.itemOutputList = [];
            for (const key in monOutput) {
                if (Object.hasOwnProperty.call(monOutput, key)) {
                    const element = monOutput[key].split(",");
                    if (element.includes(this.selectItem.key)) {
                        this.itemOutputList.push(key)
                    }
                }
            }
        },
        // 选中物品产出触发
        selectItemOutputFn(item) {
            this.selectItemOutput = item;
            // 获取刷怪列表
            this.getMonGenList(item)
        },
        /**
         *************************************** 怪物
         */
        // 选中怪物触发
        selectMonFn(item) {
            if (this.selectMon == item) {
                this.selectMon = ""
            } else {
                this.selectMon = item;
            }
            // 获取怪物产出
            this.getMonOutput()
            // 获取刷怪列表
            this.getMonGenList(this.selectMon)
        },
        // 获取怪物列表
        getMonList(val) {
            this.loading = true;
            if (this.defaultQueryUse.mon == 1) {
                this.monList = mons.filter(el => val ? el.indexOf(val) != -1 : el)
            } else {
                let tempMonList = mons.filter(el => val ? el.indexOf(val) != -1 : el);
                let endMonList = tempMonList.filter(el => !!monOutput[el])
                if (this.defaultQueryUse.mon == 3) {
                    let findMongen = JSON.stringify(mongen);
                    endMonList = endMonList.filter(el => findMongen.indexOf(" " + el + " ") != -1);
                }
                this.monList = [...endMonList];
            }
            setTimeout(() => {
                this.loading = false;
            }, 200);
        },
        // 获取怪物产出
        getMonOutput() {
            if (!this.selectMon) {
                this.monOutputList = [];
                return
            }
            this.monOutputList = monOutput[this.selectMon] ? monOutput[this.selectMon].split(",") : [];
        },
        /**
         *************************************** 刷怪列表
         */
        getMonGenList(item) {
            this.monGenList = [];
            if (!item) {
                return
            }
            let filterMonGen = mongen.filter(el => el.indexOf(item.toUpperCase()) != -1);
            filterMonGen.forEach(el => {
                let tempArr = el.split(" ");
                this.monGenList.push({
                    map: tempArr[0].toUpperCase(),
                    x: tempArr[1],
                    y: tempArr[2],
                    f: tempArr[4],
                    num: tempArr[5],
                    time: tempArr[6]
                })
            })
        },
        // 刷怪间隔显示: 自用版(换算) 显示 XX(实际YY)/分钟; 发布版(原始) 显示 XX/分钟
        formatMonGenTime(time) {
            let t = parseInt(time, 10);
            if (isNaN(t)) {
                return time;
            }
            if (!MON_GEN_TIME_REAL) {
                return t + " / 分钟";
            }
            if (t < 60) {
                return t + " / 分钟";
            }
            let real = Math.floor(t / 3);
            if (real > 60) {
                real = 60;
            }
            return t + "（实际" + real + "）/ 分钟";
        },
        // 刷怪列表点击地图触发
        monGenMapClick(item) {
            if (this.selectMap.key == item.map) {
                this.selectMap = {};
            } else {
                this.selectMap = {
                    item: this.allMapInfo[item.map],
                    key: item.map
                };
            }
            // 获取地图走法
            this.getMapGoInfo();
        },
        /**
         *************************************** 地图信息
         */
        getMapInfoObj(val) {
            this.loading = true;
            this.mapInfoObj = {};
            if (!val) {
                this.mapInfoObj = { ...mapInfo }
            } else {
                for (const key in mapInfo) {
                    if (Object.hasOwnProperty.call(mapInfo, key)) {
                        const element = mapInfo[key].toUpperCase();
                        if (key.indexOf(val.toUpperCase()) != -1 || element.indexOf(val.toUpperCase()) != -1) {
                            this.mapInfoObj[key] = element
                        }
                    }
                }
            }
            if (this.defaultQueryUse.map == 2) {
                let newMapInfoObj = {};
                for (const key in this.mapInfoObj) {
                    if (Object.hasOwnProperty.call(this.mapInfoObj, key)) {
                        const element = this.mapInfoObj[key];
                        let findMongen = JSON.stringify(mongen);
                        if (findMongen.indexOf('"' + key + " ") != -1) {
                            newMapInfoObj[key] = element;
                        }
                        let findNpc = merchant.filter(npc => {
                            let rowNpc = npc.split(" ");
                            return rowNpc[1] == key;
                        })
                        if (findNpc.length > 0) {
                            newMapInfoObj[key] = element;
                        }
                    }
                }
                this.mapInfoObj = { ...newMapInfoObj };
            }
            setTimeout(() => {
                this.loading = false;
            }, 200);
        },
        // 选中地图触发
        selectMapFn(item, key) {
            if (this.selectMap.key == key) {
                this.selectMap = {}
            } else {
                this.selectMap = {
                    item,
                    key
                }
            }
            // 地图刷怪列表
            this.getMapMonList()
            // 地图NPC列表
            this.getMapNpcList()
            // 获取地图走法
            this.getMapGoInfo();
        },
        // 地图刷怪列表
        getMapMonList() {
            this.mapMonList = [];
            if (!this.selectMap.key) {
                return
            }
            mongen.forEach(el => {
                let tempArr = el.split(" ");
                if (tempArr[0].toUpperCase() == this.selectMap.key.toUpperCase()) {
                    this.mapMonList.push(tempArr[3])
                }
            })
        },
        // 地图NPC列表
        getMapNpcList() {
            this.mapNpcList = [];
            if (!this.selectMap.item) {
                return
            }
            if (!this.selectMap.key) {
                return
            }
            merchant.forEach(el => {
                let tempArr = el.split(" ");
                if (tempArr.length > 0) {
                    let newArr = tempArr.filter(el => el != '');
                    let npcMap = newArr[1] ? newArr[1].toUpperCase() : "";
                    if (npcMap == this.selectMap.key.toUpperCase()) {
                        let npcFile = newArr[0].split("|").pop();
                        this.mapNpcList.push(this.getNpcName(newArr[4], npcFile) + " " + newArr[2] + "," + newArr[3])
                    }
                }
            })
        },
        // 反向追溯当前地图的上级入口链路
        getMapGoInfo() {
            if (!this.selectMap.item) {
                this.mapGoInfo = [];
                return
            }
            const routes = [];
            // 防止 hub 地图路径爆炸: 限制递归深度和总路径数
            const MAX_DEPTH = 10;
            const MAX_ROUTES = 200;
                const walkUpstream = (mapName, route, visited, depth) => {
                    if (routes.length >= MAX_ROUTES) { return; }
                    if (depth > MAX_DEPTH) { return; }
                    const parents = this.mapGoDb.filter(el => el.to === mapName && !visited.has(el.from));
                    if (parents.length === 0) {
                    if (route.length > 0) {
                        routes.push(route.map(this.formatMapGo));
                    }
                    return
                }
                parents.forEach(parent => {
                    const nextVisited = new Set(visited);
                        nextVisited.add(parent.from);
                    walkUpstream(parent.from, [parent, ...route], nextVisited, depth + 1);
                })
            }
                walkUpstream(this.selectMap.item, [], new Set([this.selectMap.item]), 0);
            const uniqueRoutes = new Map();
            routes.forEach(route => uniqueRoutes.set(route.join("\n"), route));
            this.mapGoInfo = [...uniqueRoutes.values()];
            this.mapNpcGoList = this.getNpcMapGoList();
        },
        formatMapGo(item) {
            return item.from + " " + item.fromPos + " => " + item.to + " " + item.toPos;
        },
        // 格式化地图入口数据库
        formatMapGoDb() {
            this.mapGoDb = [];
            mapGo.forEach(el => {
                    const matched = el.match(/^(.*?)\s+(\d+(?:,\d+)?(?:\s+\d+(?:,\d+)?)?)\s+->\s+(.*?)\s+(\d+(?:,\d+)?(?:\s+\d+(?:,\d+)?)?)\s*$/);
                if (matched) {
                    const from = mapInfo[matched[1].toUpperCase()];
                    const to = mapInfo[matched[3].toUpperCase()];
                    if (from && to) {
                        this.mapGoDb.push({ from, fromPos: matched[2], to, toPos: matched[4] });
                    }
                }
            })
        },
        getNpcMapGoList() {
            if (typeof npcMapGo === "undefined") {
                return [];
            }
            const key = this.selectMap.key || "";
            const item = this.selectMap.item || "";
            let list = npcMapGo[key.toUpperCase()] || [];
            if (list.length < 1 && item) {
                list = npcMapGo[item.toUpperCase()] || [];
            }
            return list;
        },
        /**
        *************************************** npc信息
        */
        getNpcList(val) {
            this.loading = true;
            this.npcList = [];
            merchant.forEach(el => {
                let tempArr = el.split(" ");
                if (tempArr.length > 3) {
                    let newArr = tempArr.filter(el => el != '');
                    let npcFile = (newArr[0] || "").split("|").pop();
                    let mapName = newArr[1] ? (mapInfo[newArr[1].toUpperCase()] || newArr[1]) : "";
                    if (val) {
                        if (newArr[4] && newArr[4].indexOf(val) != -1) {
                            this.npcList.push(this.getNpcName(newArr[4], npcFile) + "---" + mapName + '[' + newArr[2] + "," + newArr[3] + ']')
                        }
                    } else {
                        this.npcList.push(this.getNpcName(newArr[4], npcFile) + "---" + mapName + '[' + newArr[2] + "," + newArr[3] + ']')
                    }

                }
            })
            setTimeout(() => {
                this.loading = false;
            }, 200);
        },
        getNpcName(str, file) {
            if (str == 1 || str == 0 || str == "　") {
                return file ? "图标NPC(" + file + ")" : "图标NPC"
            } else {
                return str
            }
        },
        /** 双击怪物查看详细产出 */
        dbclickMon(mon) {
            if (this.isDbClickMon) {

                this.$message.info("以为您打开" + mon + ".txt，如果提示未找到文件就是该怪物没有爆率！")
                this.$nextTick(() => {
                    window.open("./MonItems/" + mon + ".txt")
                })
            }
        },
        // 显示过滤条件
        showQueryOps(menu) {
            if (menu == 'npc') {
                return false;
            }
            if (menu == 'item' || menu == 'map') {
                return this[menu + 'QueryType'] == 3;
            } else {
                return this.monQueryType == 4;
            }
        },
        // 获取过滤条件op
        getQeuryOps(menu) {
            if (menu == 'npc') {
                return []
            }
            return this[menu + 'QueryList'];
        },
    }

};
const app = Vue.createApp(App);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}
app.use(ElementPlus);
app.mount("#app");
