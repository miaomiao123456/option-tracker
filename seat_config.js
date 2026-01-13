// 席位类型配置文件
// 可在此处配置哪些是机构席位，哪些是散户席位

const SEAT_CONFIG = {
    // 机构席位列表
    institutional_seats: [
        "中信期货", "国泰君安", "海通期货", "银河期货", "华泰期货",
        "申银万国", "广发期货", "招商期货", "中金期货", "中信建投",
        "光大期货", "南华期货", "永安期货", "国投安信", "东证期货",
        "方正中期", "浙商期货", "平安期货", "兴证期货", "国信期货"
    ],

    // 散户集中的席位（通常是一些小型期货公司或营业部）
    retail_seats: [
        "一德期货", "金瑞期货", "大地期货", "中投天琪", "东吴期货",
        "锦泰期货", "华闻期货", "西南期货", "东方财富", "同花顺期货",
        "长江期货", "弘业期货", "徽商期货", "东海期货", "国贸期货"
    ],

    // 根据名称判断席位类型的规则
    rules: {
        // 包含以下关键词的视为机构席位
        institutional_keywords: ["中信", "国泰", "海通", "银河", "华泰", "中金", "国投", "平安", "招商", "广发"],

        // 包含以下关键词的视为散户席位
        retail_keywords: ["营业部", "散户", "个人", "东方财富", "同花顺", "小散"]
    },

    // 获取席位类型
    getSeatType: function(seatName) {
        // 先检查是否在配置的机构列表中
        if (this.institutional_seats.includes(seatName)) {
            return 'institutional';
        }

        // 检查是否在散户列表中
        if (this.retail_seats.includes(seatName)) {
            return 'retail';
        }

        // 按关键词判断
        for (let keyword of this.rules.institutional_keywords) {
            if (seatName.includes(keyword)) {
                return 'institutional';
            }
        }

        for (let keyword of this.rules.retail_keywords) {
            if (seatName.includes(keyword)) {
                return 'retail';
            }
        }

        // 默认归为其他
        return 'other';
    },

    // 批量获取席位类型统计
    getSeatsStatistics: function(seatsList) {
        const stats = {
            institutional: [],
            retail: [],
            other: []
        };

        for (let seat of seatsList) {
            const type = this.getSeatType(seat.name || seat);
            stats[type].push(seat);
        }

        return stats;
    }
};

// 导出配置（如果使用模块化）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SEAT_CONFIG;
}