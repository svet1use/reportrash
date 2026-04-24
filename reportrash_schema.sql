-- ============================================================
--  ReporTrash — MySQL Database Schema
--  Generated from models.py
--  User: root / Pass: root
-- ============================================================

CREATE DATABASE IF NOT EXISTS reportrash
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE reportrash;

-- ============================================================
-- 1. Django built-in: auth_user
-- ============================================================
CREATE TABLE IF NOT EXISTS auth_user (
    id           INT          NOT NULL AUTO_INCREMENT,
    password     VARCHAR(128) NOT NULL,
    last_login   DATETIME(6)  DEFAULT NULL,
    is_superuser TINYINT(1)   NOT NULL DEFAULT 0,
    username     VARCHAR(150) NOT NULL UNIQUE,
    first_name   VARCHAR(150) NOT NULL DEFAULT '',
    last_name    VARCHAR(150) NOT NULL DEFAULT '',
    email        VARCHAR(254) NOT NULL DEFAULT '',
    is_staff     TINYINT(1)   NOT NULL DEFAULT 0,
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,
    date_joined  DATETIME(6)  NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ============================================================
-- 2. BarangayProfile  (OneToOne -> auth_user)
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_barangayprofile (
    id                    BIGINT       NOT NULL AUTO_INCREMENT,
    user_id               INT          NOT NULL UNIQUE,
    barangay_name         VARCHAR(100) NOT NULL DEFAULT 'Barangay 1',
    purok                 VARCHAR(50)  NOT NULL DEFAULT '',
    address               LONGTEXT     NOT NULL,
    contact_number        VARCHAR(20)  NOT NULL DEFAULT '',
    avatar_color          VARCHAR(7)   NOT NULL DEFAULT '#22c55e',
    profile_picture       VARCHAR(100) DEFAULT NULL,
    points                INT          NOT NULL DEFAULT 0,
    level                 VARCHAR(50)  NOT NULL DEFAULT 'Eco Starter',
    created_at            DATETIME(6)  NOT NULL,
    notification_settings JSON         NOT NULL,
    is_profile_public     TINYINT(1)   NOT NULL DEFAULT 1,
    show_email            TINYINT(1)   NOT NULL DEFAULT 0,
    show_location         TINYINT(1)   NOT NULL DEFAULT 1,
    allow_messages        TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    CONSTRAINT fk_bp_user FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 3. WasteReport
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_wastereport (
    id                  BIGINT         NOT NULL AUTO_INCREMENT,
    reporter_id         INT            NOT NULL,
    title               VARCHAR(200)   NOT NULL,
    category            VARCHAR(50)    NOT NULL
                        COMMENT 'biodegradable|recyclable|residual|special|hazardous|electronic',
    location            VARCHAR(200)   NOT NULL,
    purok               VARCHAR(50)    NOT NULL DEFAULT '',
    description         LONGTEXT       NOT NULL,
    status              VARCHAR(20)    NOT NULL DEFAULT 'pending'
                        COMMENT 'pending|collected|processed|disposed',
    image               VARCHAR(100)   DEFAULT NULL,
    reported_at         DATETIME(6)    NOT NULL,
    collected_at        DATETIME(6)    DEFAULT NULL,
    notes               LONGTEXT       NOT NULL,
    points_awarded      INT            NOT NULL DEFAULT 0,
    latitude            DECIMAL(10, 7) DEFAULT NULL,
    longitude           DECIMAL(10, 7) DEFAULT NULL,
    address             LONGTEXT       DEFAULT NULL,
    image_hash          VARCHAR(64)    DEFAULT NULL,
    verification_passed TINYINT(1)     NOT NULL DEFAULT 0,
    verification_data   JSON           NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_wr_reporter FOREIGN KEY (reporter_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    INDEX idx_wr_image_hash          (image_hash),
    INDEX idx_wr_verification_passed (verification_passed),
    INDEX idx_wr_status_reported     (status, reported_at)
) ENGINE=InnoDB;

-- ============================================================
-- 4. CollectionSchedule
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_collectionschedule (
    id             BIGINT       NOT NULL AUTO_INCREMENT,
    day_of_week    VARCHAR(20)  NOT NULL
                   COMMENT 'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
    waste_category VARCHAR(50)  NOT NULL
                   COMMENT 'biodegradable|recyclable|residual|special|hazardous|electronic',
    time_start     TIME(6)      NOT NULL,
    time_end       TIME(6)      NOT NULL,
    purok          VARCHAR(50)  NOT NULL DEFAULT 'All',
    collector_name VARCHAR(100) NOT NULL DEFAULT '',
    is_active      TINYINT(1)   NOT NULL DEFAULT 1,
    notes          LONGTEXT     NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ============================================================
-- 5. Announcement
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_announcement (
    id                BIGINT       NOT NULL AUTO_INCREMENT,
    title             VARCHAR(200) NOT NULL,
    content           LONGTEXT     NOT NULL,
    priority          VARCHAR(10)  NOT NULL DEFAULT 'medium'
                      COMMENT 'low|medium|high|urgent',
    created_by_id     INT          NOT NULL,
    created_at        DATETIME(6)  NOT NULL,
    updated_at        DATETIME(6)  NOT NULL,
    is_active         TINYINT(1)   NOT NULL DEFAULT 1,
    emoji             VARCHAR(10)  NOT NULL DEFAULT '',
    target_barangay   VARCHAR(100) NOT NULL DEFAULT '',
    send_notification TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    CONSTRAINT fk_ann_creator FOREIGN KEY (created_by_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 6. CommunityPost
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_communitypost (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    author_id    INT          NOT NULL,
    content      LONGTEXT     NOT NULL,
    image        VARCHAR(100) DEFAULT NULL,
    created_at   DATETIME(6)  NOT NULL,
    is_tip       TINYINT(1)   NOT NULL DEFAULT 0,
    tip_category VARCHAR(50)  NOT NULL DEFAULT '',
    PRIMARY KEY (id),
    CONSTRAINT fk_cp_author FOREIGN KEY (author_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 7. CommunityPost_likes  (ManyToMany: CommunityPost <-> User)
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_communitypost_likes (
    id               BIGINT NOT NULL AUTO_INCREMENT,
    communitypost_id BIGINT NOT NULL,
    user_id          INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_post_like (communitypost_id, user_id),
    CONSTRAINT fk_cpl_post FOREIGN KEY (communitypost_id)
        REFERENCES waste_management_communitypost (id) ON DELETE CASCADE,
    CONSTRAINT fk_cpl_user FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 8. CommunityReply
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_communityreply (
    id              BIGINT      NOT NULL AUTO_INCREMENT,
    post_id         BIGINT      NOT NULL,
    author_id       INT         NOT NULL,
    content         LONGTEXT    NOT NULL,
    created_at      DATETIME(6) NOT NULL,
    parent_reply_id BIGINT      DEFAULT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_cr_post   FOREIGN KEY (post_id)
        REFERENCES waste_management_communitypost (id) ON DELETE CASCADE,
    CONSTRAINT fk_cr_author FOREIGN KEY (author_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_cr_parent FOREIGN KEY (parent_reply_id)
        REFERENCES waste_management_communityreply (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 9. CommunityReply_likes  (ManyToMany: CommunityReply <-> User)
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_communityreply_likes (
    id                BIGINT NOT NULL AUTO_INCREMENT,
    communityreply_id BIGINT NOT NULL,
    user_id           INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_reply_like (communityreply_id, user_id),
    CONSTRAINT fk_crl_reply FOREIGN KEY (communityreply_id)
        REFERENCES waste_management_communityreply (id) ON DELETE CASCADE,
    CONSTRAINT fk_crl_user  FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- 10. Notification
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_notification (
    id                BIGINT       NOT NULL AUTO_INCREMENT,
    user_id           INT          NOT NULL,
    announcement_id   BIGINT       DEFAULT NULL,
    related_report_id BIGINT       DEFAULT NULL,
    related_post_id   BIGINT       DEFAULT NULL,
    actor_id          INT          DEFAULT NULL,
    title             VARCHAR(200) NOT NULL,
    message           LONGTEXT     NOT NULL,
    is_read           TINYINT(1)   NOT NULL DEFAULT 0,
    created_at        DATETIME(6)  NOT NULL,
    notification_type VARCHAR(50)  NOT NULL DEFAULT 'announcement'
                      COMMENT 'announcement|report|level_up|collection|system|like|reply|share',
    PRIMARY KEY (id),
    CONSTRAINT fk_notif_user   FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_ann    FOREIGN KEY (announcement_id)
        REFERENCES waste_management_announcement (id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_report FOREIGN KEY (related_report_id)
        REFERENCES waste_management_wastereport (id) ON DELETE SET NULL,
    CONSTRAINT fk_notif_post   FOREIGN KEY (related_post_id)
        REFERENCES waste_management_communitypost (id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_actor  FOREIGN KEY (actor_id)
        REFERENCES auth_user (id) ON DELETE SET NULL,
    INDEX idx_notif_user_read (user_id, is_read),
    INDEX idx_notif_created   (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- 11. WasteStats
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_wastestats (
    id                     BIGINT        NOT NULL AUTO_INCREMENT,
    month                  DATE          NOT NULL,
    total_biodegradable_kg DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_recyclable_kg    DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_residual_kg      DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_special_kg       DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_hazardous_kg     DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_electronic_kg    DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_reports          INT           NOT NULL DEFAULT 0,
    collection_rate        DECIMAL(5,2)  NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ============================================================
-- 12. UserFollow
-- ============================================================
CREATE TABLE IF NOT EXISTS waste_management_userfollow (
    id           BIGINT      NOT NULL AUTO_INCREMENT,
    follower_id  INT         NOT NULL,
    following_id INT         NOT NULL,
    created_at   DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_follow (follower_id, following_id),
    CONSTRAINT fk_uf_follower  FOREIGN KEY (follower_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_uf_following FOREIGN KEY (following_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- Django system tables (required by manage.py)
-- ============================================================
CREATE TABLE IF NOT EXISTS django_migrations (
    id      BIGINT       NOT NULL AUTO_INCREMENT,
    app     VARCHAR(255) NOT NULL,
    name    VARCHAR(255) NOT NULL,
    applied DATETIME(6)  NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS django_content_type (
    id        INT          NOT NULL AUTO_INCREMENT,
    app_label VARCHAR(100) NOT NULL,
    model     VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_app_model (app_label, model)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_permission (
    id              INT          NOT NULL AUTO_INCREMENT,
    name            VARCHAR(255) NOT NULL,
    content_type_id INT          NOT NULL,
    codename        VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_perm (content_type_id, codename),
    CONSTRAINT fk_perm_ct FOREIGN KEY (content_type_id)
        REFERENCES django_content_type (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_group (
    id   INT          NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL UNIQUE,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id            BIGINT NOT NULL AUTO_INCREMENT,
    group_id      INT    NOT NULL,
    permission_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_group_perm (group_id, permission_id),
    CONSTRAINT fk_gp_group FOREIGN KEY (group_id)
        REFERENCES auth_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_gp_perm  FOREIGN KEY (permission_id)
        REFERENCES auth_permission (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_user_groups (
    id       BIGINT NOT NULL AUTO_INCREMENT,
    user_id  INT    NOT NULL,
    group_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_group (user_id, group_id),
    CONSTRAINT fk_ug_user  FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_ug_group FOREIGN KEY (group_id)
        REFERENCES auth_group (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id            BIGINT NOT NULL AUTO_INCREMENT,
    user_id       INT    NOT NULL,
    permission_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_perm (user_id, permission_id),
    CONSTRAINT fk_up_user FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_up_perm FOREIGN KEY (permission_id)
        REFERENCES auth_permission (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS django_session (
    session_key  VARCHAR(40) NOT NULL,
    session_data LONGTEXT    NOT NULL,
    expire_date  DATETIME(6) NOT NULL,
    PRIMARY KEY (session_key),
    INDEX idx_session_expire (expire_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS django_admin_log (
    id              INT          NOT NULL AUTO_INCREMENT,
    action_time     DATETIME(6)  NOT NULL,
    object_id       LONGTEXT     DEFAULT NULL,
    object_repr     VARCHAR(200) NOT NULL,
    action_flag     SMALLINT UNSIGNED NOT NULL,
    change_message  LONGTEXT     NOT NULL,
    content_type_id INT          DEFAULT NULL,
    user_id         INT          NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_al_ct   FOREIGN KEY (content_type_id)
        REFERENCES django_content_type (id) ON DELETE SET NULL,
    CONSTRAINT fk_al_user FOREIGN KEY (user_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;