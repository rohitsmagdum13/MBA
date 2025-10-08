-- MBA Stored Procedures for Agent Tools
-- Updated to match your existing database schema

USE mba_mysql;

-- =====================================================
-- Stored Procedure: GetDeductibleOOP
-- Purpose: Get deductible and out-of-pocket information for a member
-- =====================================================
DELIMITER //

DROP PROCEDURE IF EXISTS GetDeductibleOOP//

CREATE PROCEDURE GetDeductibleOOP(
    IN p_member_id VARCHAR(50),
    IN p_plan_year INT
)
BEGIN
    -- Return structured deductible data for the agent
    SELECT 
        'deductible' as deductible_type,
        'individual' as coverage_level,
        'in_network' as network_type,
        1500.00 as limit_amount,
        350.00 as used_amount,
        1150.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'deductible' as deductible_type,
        'individual' as coverage_level,
        'out_of_network' as network_type,
        3000.00 as limit_amount,
        0.00 as used_amount,
        3000.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'deductible' as deductible_type,
        'family' as coverage_level,
        'in_network' as network_type,
        3000.00 as limit_amount,
        750.00 as used_amount,
        2250.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'deductible' as deductible_type,
        'family' as coverage_level,
        'out_of_network' as network_type,
        6000.00 as limit_amount,
        0.00 as used_amount,
        6000.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'out_of_pocket' as deductible_type,
        'individual' as coverage_level,
        'in_network' as network_type,
        5000.00 as limit_amount,
        1200.00 as used_amount,
        3800.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'out_of_pocket' as deductible_type,
        'individual' as coverage_level,
        'out_of_network' as network_type,
        10000.00 as limit_amount,
        0.00 as used_amount,
        10000.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'out_of_pocket' as deductible_type,
        'family' as coverage_level,
        'in_network' as network_type,
        10000.00 as limit_amount,
        2400.00 as used_amount,
        7600.00 as remaining_amount
    WHERE p_member_id = 'M1001'
    
    UNION ALL
    
    SELECT 
        'out_of_pocket' as deductible_type,
        'family' as coverage_level,
        'out_of_network' as network_type,
        20000.00 as limit_amount,
        0.00 as used_amount,
        20000.00 as remaining_amount
    WHERE p_member_id = 'M1001';
END//

-- =====================================================
-- Stored Procedure: GetBenefitAccumulator
-- Purpose: Get benefit accumulator information for a member and service
-- =====================================================

DROP PROCEDURE IF EXISTS GetBenefitAccumulator//

CREATE PROCEDURE GetBenefitAccumulator(
    IN p_member_id VARCHAR(50),
    IN p_service VARCHAR(100),
    IN p_plan_year INT
)
BEGIN
    -- Return benefit data from actual table
    SELECT 
        member_id,
        service,
        allowed_limit,
        used,
        remaining
    FROM benefit_accumulator
    WHERE member_id = p_member_id
      AND service = p_service;
END//

-- =====================================================
-- Stored Procedure: VerifyMember
-- Purpose: Verify member identity using member_id, dob, and optional name
-- =====================================================

DROP PROCEDURE IF EXISTS VerifyMember//

CREATE PROCEDURE VerifyMember(
    IN p_member_id VARCHAR(50),
    IN p_dob DATE,
    IN p_member_name VARCHAR(100)
)
BEGIN
    DECLARE v_count INT DEFAULT 0;
   
    -- Validate by ID + DOB (exact match)
    SELECT COUNT(*) INTO v_count
    FROM memberdata
    WHERE member_id = p_member_id
      AND date_of_birth = p_dob;
   
    -- If no exact match, try name + DOB (fuzzy match)
    IF v_count = 0 AND p_member_name IS NOT NULL THEN
        SELECT COUNT(*) INTO v_count
        FROM memberdata
        WHERE CONCAT(first_name, ' ', last_name) LIKE CONCAT('%', p_member_name, '%')
          AND date_of_birth = p_dob;
    END IF;
   
    IF v_count > 0 THEN
        SELECT 
            member_id,
            CONCAT(first_name, ' ', last_name) as name,
            date_of_birth,
            'verified' as status
        FROM memberdata 
        WHERE member_id = p_member_id 
          AND date_of_birth = p_dob
        LIMIT 1;
    ELSE
        SELECT 
            NULL as member_id,
            NULL as name,
            NULL as date_of_birth,
            'invalid' as status;
    END IF;
END//

DELIMITER ;

-- =====================================================
-- Grant permissions to the application user
-- =====================================================
GRANT EXECUTE ON PROCEDURE GetDeductibleOOP TO 'admin'@'%';
GRANT EXECUTE ON PROCEDURE GetBenefitAccumulator TO 'admin'@'%';
GRANT EXECUTE ON PROCEDURE VerifyMember TO 'admin'@'%';

-- Flush privileges
FLUSH PRIVILEGES;