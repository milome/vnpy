# Generated from mflang/grammar/MFLang.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .MFLangParser import MFLangParser
else:
    from MFLangParser import MFLangParser

# This class defines a complete generic visitor for a parse tree produced by MFLangParser.

class MFLangVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by MFLangParser#program.
    def visitProgram(self, ctx:MFLangParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#statement.
    def visitStatement(self, ctx:MFLangParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#importStatement.
    def visitImportStatement(self, ctx:MFLangParser.ImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#periodType.
    def visitPeriodType(self, ctx:MFLangParser.PeriodTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#variableDeclaration.
    def visitVariableDeclaration(self, ctx:MFLangParser.VariableDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#variableAssignment.
    def visitVariableAssignment(self, ctx:MFLangParser.VariableAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#tradingInstruction.
    def visitTradingInstruction(self, ctx:MFLangParser.TradingInstructionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#tradingCmd.
    def visitTradingCmd(self, ctx:MFLangParser.TradingCmdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#tCommandStatement.
    def visitTCommandStatement(self, ctx:MFLangParser.TCommandStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#ifThenBlock.
    def visitIfThenBlock(self, ctx:MFLangParser.IfThenBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#blockStatement.
    def visitBlockStatement(self, ctx:MFLangParser.BlockStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#emptyStatement.
    def visitEmptyStatement(self, ctx:MFLangParser.EmptyStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#ComparisonExpression.
    def visitComparisonExpression(self, ctx:MFLangParser.ComparisonExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#AdditiveExpression.
    def visitAdditiveExpression(self, ctx:MFLangParser.AdditiveExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#AndExpression.
    def visitAndExpression(self, ctx:MFLangParser.AndExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#OrKeywordExpression.
    def visitOrKeywordExpression(self, ctx:MFLangParser.OrKeywordExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#NotKeywordExpression.
    def visitNotKeywordExpression(self, ctx:MFLangParser.NotKeywordExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#NotExpression.
    def visitNotExpression(self, ctx:MFLangParser.NotExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#UnaryExpression.
    def visitUnaryExpression(self, ctx:MFLangParser.UnaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#PrimaryExpr.
    def visitPrimaryExpr(self, ctx:MFLangParser.PrimaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#OrExpression.
    def visitOrExpression(self, ctx:MFLangParser.OrExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#AndKeywordExpression.
    def visitAndKeywordExpression(self, ctx:MFLangParser.AndKeywordExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#MultiplicativeExpression.
    def visitMultiplicativeExpression(self, ctx:MFLangParser.MultiplicativeExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#LiteralExpr.
    def visitLiteralExpr(self, ctx:MFLangParser.LiteralExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#IdentifierExpr.
    def visitIdentifierExpr(self, ctx:MFLangParser.IdentifierExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#KlineDataExpr.
    def visitKlineDataExpr(self, ctx:MFLangParser.KlineDataExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#FunctionCallExpr.
    def visitFunctionCallExpr(self, ctx:MFLangParser.FunctionCallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#CrossPeriodRefExpr.
    def visitCrossPeriodRefExpr(self, ctx:MFLangParser.CrossPeriodRefExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#ParenExpr.
    def visitParenExpr(self, ctx:MFLangParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#literal.
    def visitLiteral(self, ctx:MFLangParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#integer.
    def visitInteger(self, ctx:MFLangParser.IntegerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#float.
    def visitFloat(self, ctx:MFLangParser.FloatContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#booleanLiteral.
    def visitBooleanLiteral(self, ctx:MFLangParser.BooleanLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#stringLiteral.
    def visitStringLiteral(self, ctx:MFLangParser.StringLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#klineData.
    def visitKlineData(self, ctx:MFLangParser.KlineDataContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#functionCall.
    def visitFunctionCall(self, ctx:MFLangParser.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#refFunction.
    def visitRefFunction(self, ctx:MFLangParser.RefFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#barslastFunction.
    def visitBarslastFunction(self, ctx:MFLangParser.BarslastFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#sumbarsFunction.
    def visitSumbarsFunction(self, ctx:MFLangParser.SumbarsFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#hhvFunction.
    def visitHhvFunction(self, ctx:MFLangParser.HhvFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#llvFunction.
    def visitLlvFunction(self, ctx:MFLangParser.LlvFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#hhvbarsFunction.
    def visitHhvbarsFunction(self, ctx:MFLangParser.HhvbarsFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#llvbarsFunction.
    def visitLlvbarsFunction(self, ctx:MFLangParser.LlvbarsFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#countFunction.
    def visitCountFunction(self, ctx:MFLangParser.CountFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#maxFunction.
    def visitMaxFunction(self, ctx:MFLangParser.MaxFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#max1Function.
    def visitMax1Function(self, ctx:MFLangParser.Max1FunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#minFunction.
    def visitMinFunction(self, ctx:MFLangParser.MinFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#min1Function.
    def visitMin1Function(self, ctx:MFLangParser.Min1FunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#ifFunction.
    def visitIfFunction(self, ctx:MFLangParser.IfFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#absFunction.
    def visitAbsFunction(self, ctx:MFLangParser.AbsFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#emaFunction.
    def visitEmaFunction(self, ctx:MFLangParser.EmaFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#maFunction.
    def visitMaFunction(self, ctx:MFLangParser.MaFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#smaFunction.
    def visitSmaFunction(self, ctx:MFLangParser.SmaFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#stdFunction.
    def visitStdFunction(self, ctx:MFLangParser.StdFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#modFunction.
    def visitModFunction(self, ctx:MFLangParser.ModFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#hvFunction.
    def visitHvFunction(self, ctx:MFLangParser.HvFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#lvFunction.
    def visitLvFunction(self, ctx:MFLangParser.LvFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#timeFunction.
    def visitTimeFunction(self, ctx:MFLangParser.TimeFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#betweenFunction.
    def visitBetweenFunction(self, ctx:MFLangParser.BetweenFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#crossPeriodRef.
    def visitCrossPeriodRef(self, ctx:MFLangParser.CrossPeriodRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#formatOption.
    def visitFormatOption(self, ctx:MFLangParser.FormatOptionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#identifier.
    def visitIdentifier(self, ctx:MFLangParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#rgbFunction.
    def visitRgbFunction(self, ctx:MFLangParser.RgbFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#drawStatement.
    def visitDrawStatement(self, ctx:MFLangParser.DrawStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#drawArg.
    def visitDrawArg(self, ctx:MFLangParser.DrawArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#drawFunction.
    def visitDrawFunction(self, ctx:MFLangParser.DrawFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MFLangParser#formatOnlyStatement.
    def visitFormatOnlyStatement(self, ctx:MFLangParser.FormatOnlyStatementContext):
        return self.visitChildren(ctx)



del MFLangParser