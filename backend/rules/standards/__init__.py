accommodation_standards = {
    "tier_1": {
        "regular": {
            "daily_limit": 450,
            "description": "一类城市普通员工住宿标准",
            "cities": ["北京", "上海", "广州", "深圳"]
        },
        "management": {
            "daily_limit": 800,
            "description": "一类城市管理层住宿标准",
            "cities": ["北京", "上海", "广州", "深圳"]
        }
    },
    "tier_2": {
        "regular": {
            "daily_limit": 350,
            "description": "二类城市普通员工住宿标准",
            "cities": ["成都", "杭州", "南京", "武汉", "西安", "郑州", "长沙", "沈阳", "青岛", "济南", "大连", "宁波", "厦门", "福州", "无锡", "合肥"]
        },
        "management": {
            "daily_limit": 600,
            "description": "二类城市管理层住宿标准",
            "cities": ["成都", "杭州", "南京", "武汉", "西安", "郑州", "长沙", "沈阳", "青岛", "济南", "大连", "宁波", "厦门", "福州", "无锡", "合肥"]
        }
    },
    "tier_3": {
        "regular": {
            "daily_limit": 280,
            "description": "三类及以下城市普通员工住宿标准"
        },
        "management": {
            "daily_limit": 450,
            "description": "三类及以下城市管理层住宿标准"
        }
    }
}

transport_standards = {
    "air": {
        "regular": {
            "allowed_seats": ["经济舱"],
            "description": "普通员工仅允许经济舱"
        },
        "management": {
            "allowed_seats": ["公务舱", "全价经济舱", "经济舱"],
            "description": "管理层允许公务舱或全价经济舱"
        }
    },
    "train": {
        "regular": {
            "allowed_seats": ["二等座"],
            "description": "普通员工仅允许二等座"
        },
        "management": {
            "allowed_seats": ["一等座", "二等座"],
            "description": "管理层允许一等座"
        },
        "night_allowed": {
            "regular": ["硬卧", "硬座"],
            "management": ["软卧", "硬卧", "软座", "硬座"]
        }
    },
    "regular": {
        "regular": {
            "allowed_seats": ["硬卧", "硬座"],
            "description": "普通员工允许硬卧/硬座"
        },
        "management": {
            "allowed_seats": ["软卧", "硬卧", "软座", "硬座"],
            "description": "管理层允许软卧"
        }
    },
    "ship": {
        "regular": {
            "allowed_seats": ["三等舱"],
            "description": "普通员工仅允许三等舱"
        },
        "management": {
            "allowed_seats": ["二等舱", "三等舱"],
            "description": "管理层允许二等舱"
        }
    }
}

daily_standards = {
    "city_transport": {
        "regular": {
            "daily": 80,
            "description": "普通员工市内交通补助 80元/天"
        },
        "management": {
            "daily": 150,
            "description": "管理层市内交通补助 150元/天"
        }
    },
    "meal": {
        "regular": {
            "daily": 100,
            "description": "普通员工伙食补助 100元/天"
        },
        "management": {
            "daily": 150,
            "description": "管理层伙食补助 150元/天"
        }
    }
}

business_entertainment_standards = {
    "regular": {
        "per_person": 150,
        "description": "普通员工业务招待人均标准 150元/人"
    },
    "management": {
        "per_person": 300,
        "description": "管理层业务招待人均标准 300元/人"
    }
}
